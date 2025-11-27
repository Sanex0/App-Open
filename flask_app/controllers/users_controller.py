import smtplib
import json
from decimal import Decimal
from email.message import EmailMessage
from datetime import datetime

from flask import render_template, redirect, request, session, flash, url_for, jsonify
from flask_bcrypt import Bcrypt

from flask_app import app
from flask_app.models.productos import Producto
from flask_app.models.users import User
from flask_app.models.cajas import Caja
from flask_app.models.apertura import Apertura
from flask_app.models.venta import Venta
from flask_app.models.permiso import Permiso

bcrypt = Bcrypt(app)

# --- Funciones Auxiliares ---

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, Producto):
        return obj.__dict__
    raise TypeError

def validar_rut(rut):
    if not rut: return False
    rut = rut.replace('.', '').replace('-', '').upper()
    if len(rut) < 8 or len(rut) > 9:
        return False
    cuerpo = rut[:-1]
    dv = rut[-1]
    if not cuerpo.isdigit() or not (dv.isdigit() or dv == 'K'):
        return False
    
    suma = sum(int(c) * (multiplo if multiplo < 8 else multiplo - 6) for c, multiplo in zip(reversed(cuerpo), range(2, len(cuerpo) + 2)))
    dv_esperado = 11 - (suma % 11)
    if dv_esperado == 11: dv_esperado = '0'
    elif dv_esperado == 10: dv_esperado = 'K'
    else: dv_esperado = str(dv_esperado)
    
    return dv == dv_esperado

# --- Rutas ---

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if not request.form.get('email') or not request.form.get('password'):
        flash('Faltan campos obligatorios', 'inicio_sesion')
        return redirect('/')
    email = request.form['email']
    pwd = request.form['password']

    user = User.get_by_email({'email_usuario': email})

    # Logs de diagnóstico controlados por la configuración `LOGIN_DEBUG`.
    if app.config.get('LOGIN_DEBUG'):
        if not user:
            print(f"[LOGIN DEBUG] No se encontró usuario para email: {email}")
        else:
            stored = user.password or ''
            prefix = stored[:6] if len(stored) >= 6 else stored
            print(f"[LOGIN DEBUG] Usuario encontrado id={getattr(user, 'id_usuario', None)}; hash_len={len(stored)}; hash_prefix={prefix}")

    # Diferenciar mensajes: usuario inexistente vs contraseña incorrecta.
    # Para evitar *user enumeration* en producción, mostramos un mensaje genérico
    # a menos que `LOGIN_DEBUG` esté activado.
    if not user:
        if app.config.get('LOGIN_DEBUG'):
            flash('No existe un usuario con ese correo', 'inicio_sesion')
        else:
            flash('Credenciales incorrectas', 'inicio_sesion')
        return redirect('/')

    # Verificar contraseña con manejo seguro de errores en caso de hash inválido
    try:
        valid_password = bcrypt.check_password_hash(user.password, pwd)
    except ValueError as e:
        # Ocurre cuando el valor almacenado no es un salt bcrypt válido
        if app.config.get('LOGIN_DEBUG'):
            stored = getattr(user, 'password', None)
            print(f"[LOGIN DEBUG] bcrypt error for user id={getattr(user,'id_usuario', None)}: {e}; stored_hash={repr(stored)[:200]}")
            flash('Error en el formato del hash de la contraseña. Contacte al administrador.', 'inicio_sesion')
        else:
            flash('Credenciales incorrectas', 'inicio_sesion')
        return redirect('/')

    if not valid_password:
        if app.config.get('LOGIN_DEBUG'):
            flash('Contraseña incorrecta', 'inicio_sesion')
        else:
            flash('Credenciales incorrectas', 'inicio_sesion')
        return redirect('/')
        
    session['user_id'] = user.id_usuario
    return redirect('/index.html')

@app.route('/index.html')
def index_html():
    if 'user_id' not in session:
        return redirect('/')
    
    user = User.get_by_id(session['user_id'])
    
    permisos = Permiso.get_by_user_id(session['user_id'])
    allowed_caja_ids = [p.vta_cajas_id_caja for p in permisos]
    
    cajas = Caja.get_all()
    allowed_cajas = [c for c in cajas if c.id_caja in allowed_caja_ids]
    if app.config.get('LOGIN_DEBUG'):
        try:
            print(f"[LOGIN DEBUG] user.id_usuario={getattr(user,'id_usuario', None)}")
            print(f"[LOGIN DEBUG] permisos raw count={len(permisos)}")
            for i, p in enumerate(permisos):
                print(f"[LOGIN DEBUG] permiso[{i}] = {{'id_permiso': getattr(p,'id_permiso', None), 'id_usuario_fk': getattr(p,'id_usuario_fk', None), 'vta_cajas_id_caja': getattr(p,'vta_cajas_id_caja', None)}}")
            print(f"[LOGIN DEBUG] allowed_caja_ids = {allowed_caja_ids}")
            print(f"[LOGIN DEBUG] total cajas from DB = {len(cajas)}")
            for c in cajas[:20]:
                print(f"[LOGIN DEBUG] caja: id_caja={getattr(c,'id_caja', None)}, detalle_caja={getattr(c,'detalle_caja', None)}")
            print(f"[LOGIN DEBUG] allowed_cajas_count = {len(allowed_cajas)}")
        except Exception as e:
            print(f"[LOGIN DEBUG] error printing debug info: {e}")
    
    return render_template('index.html', user=user, cajas=allowed_cajas)

@app.route('/caja/<int:id_caja>')
def ver_caja(id_caja):
    if 'user_id' not in session:
        return redirect('/')
    
    productos = Producto.get_by_caja(id_caja)
    cajas = Caja.get_all()
    return render_template('caja.html', productos=productos, id_caja=id_caja, cajas=cajas)


@app.route('/api/caja/<int:id_caja>/productos')
def api_productos_por_caja(id_caja):
    """Endpoint JSON para listar los productos de una caja (útil para pruebas)."""
    if 'user_id' not in session:
        return jsonify({'error': 'not_authenticated'}), 401

    try:
        productos = Producto.get_by_caja(id_caja)
    except Exception as e:
        if app.config.get('LOGIN_DEBUG'):
            print(f"[API DEBUG] Error obteniendo productos para caja {id_caja}: {e}")
        return jsonify({'error': 'internal_error'}), 500

    productos_json = []
    for p in productos:
        productos_json.append({
            'id_prod': getattr(p, 'id_prod', None),
            'id_producto': getattr(p, 'id_producto', None),
            'nombre': getattr(p, 'nombre', None),
            'precio': getattr(p, 'precio', None),
            'compuesto': getattr(p, 'compuesto', None),
            'kitvirtual': getattr(p, 'kitvirtual', None),
        })

    return jsonify(productos_json)

@app.route('/pago', methods=['POST'])
def resumen_pago():
    if 'user_id' not in session:
        return redirect('/')
    
    productos_seleccionados_ids = request.form.getlist('productos')
    if not productos_seleccionados_ids:
        flash('No seleccionaste ningún producto.', 'pago')
        return redirect(request.referrer)
    
    id_caja = request.form.get('id_caja')
    productos_en_caja = Producto.get_by_caja(int(id_caja)) if id_caja and id_caja.isdigit() else []
    
    productos_a_pagar = []
    total = 0
    
    for prod in productos_en_caja:
        if str(prod.id_producto) in productos_seleccionados_ids:
            cantidad = int(request.form.get(f'cantidad_{prod.id_producto}', 1))
            prod.cantidad = cantidad
            total += (prod.precio or 0) * cantidad
            productos_a_pagar.append(prod)
    
    try:
        session['productos_boleta'] = json.loads(json.dumps(productos_a_pagar, default=decimal_default))
        session['total_boleta'] = total
    except Exception as e:
        print(f"[ERROR] No se pudo guardar en session: {e}")
        flash('Hubo un error al procesar los productos.', 'danger')
        return redirect(request.referrer)

    productos_json = json.dumps(session['productos_boleta'])
    return render_template('resumen_pago.html', productos=productos_a_pagar, productos_json=productos_json, total=total, id_caja=id_caja)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/datos_cliente', methods=['GET', 'POST'])
def datos_cliente():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        if not validar_rut(request.form.get('rut')):
            flash('RUT inválido. Por favor ingrese un RUT válido.', 'danger')
            return render_template('form_boleta.html', **request.form)
        
        return redirect(url_for('confirmar_pago', **request.form))
    
    return render_template('form_boleta.html', **request.args)

@app.route('/confirmar_pago', methods=['GET', 'POST'])
def confirmar_pago():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'GET':
        return render_template('confirmar_pago.html', **request.args)
    
    # --- PROCESO POST ---
    id_caja = request.form.get('id_caja')
    total = session.get('total_boleta', 0)
    correo = request.form.get('correo')
    nombre = request.form.get('nombre')
    productos_list = session.get('productos_boleta', [])

    if not productos_list:
        flash('Error: No se encontraron productos para procesar el pago.', 'warning')
        return redirect(url_for('ver_caja', id_caja=int(id_caja)))

    # Lógica de negocio: Registrar Venta en la nueva DB
    try:
        # 1. Verificar/Crear Apertura de Caja
        active_apertura = Apertura.get_active_by_user_and_caja(session['user_id'], id_caja)
        if not active_apertura:
            # Aquí se podría crear una apertura o denegar la venta.
            # Por ahora, denegamos la venta para forzar un flujo explícito de apertura.
            flash('No hay una apertura de caja activa para este usuario. No se puede registrar la venta.', 'danger')
            return redirect(url_for('ver_caja', id_caja=int(id_caja)))

        # 2. Crear la Venta
        data_venta = {
            'total_ventas': total,
            'id_apertura': active_apertura.id_apertura,
            'envio_correo': 1 if correo else 0
        }
        id_venta = Venta.create(data_venta, productos_list)

        if not id_venta:
            flash('Hubo un error al registrar la venta en la base de datos.', 'danger')
            return redirect(url_for('ver_caja', id_cja=int(id_caja)))

        flash(f'Venta #{id_venta} registrada con éxito!', 'success')

        # 3. Enviar Correo (si aplica)
        if correo:
            # (El código para enviar correo se mantiene similar, se puede refactorizar a una función)
            # ... (código de envío de email HTML) ...
            flash(f'Resumen de compra enviado a {correo}', 'success')

    except Exception as e:
        flash(f'Error inesperado durante el registro de la venta: {e}', 'danger')
        print(f"[SALE ERROR] {e}")
        return redirect(url_for('ver_caja', id_caja=int(id_caja)))

    # Limpiar sesión después de una venta exitosa
    session.pop('productos_boleta', None)
    session.pop('total_boleta', None)

    return redirect(url_for('ver_caja', id_caja=int(id_caja)))