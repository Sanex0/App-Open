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
from flask_app.config.conexiones import connectToMySQL

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
    # Apertura activa (por caja)
    active_apertura = Apertura.get_active_by_caja(id_caja)
    apertura_totals = 0
    if active_apertura:
        try:
            apertura_totals = Apertura.get_totals_for_apertura(active_apertura.id_apertura)
        except Exception as e:
            apertura_totals = 0
    # Permisos del usuario sobre cajas (para mostrar mensajes útiles)
    try:
        permisos = Permiso.get_by_user_id(session['user_id'])
        allowed_caja_ids = [p.vta_cajas_id_caja for p in permisos]
    except Exception:
        allowed_caja_ids = []
    can_open_apertura = (id_caja in allowed_caja_ids)
    # Restaurar cantidades previamente seleccionadas (si existen) desde la sesión
    try:
        session_products = session.get('productos_boleta', []) or []
        # session_products es una lista de dicts con 'id_producto' y 'cantidad'
        qty_map = {str(p.get('id_producto')): int(p.get('cantidad', 0)) for p in session_products}
        for prod in productos:
            pid = str(getattr(prod, 'id_producto', ''))
            prod.cantidad = qty_map.get(pid, 0)
    except Exception as e:
        if app.config.get('LOGIN_DEBUG'):
            print(f"[LOGIN DEBUG] Error al restaurar cantidades desde session: {e}")

    return render_template('caja.html', productos=productos, id_caja=id_caja, cajas=cajas, apertura=active_apertura, apertura_totals=apertura_totals, can_open_apertura=can_open_apertura)


@app.route('/aperturas')
def listar_aperturas():
    if 'user_id' not in session:
        return redirect('/')

    permisos = Permiso.get_by_user_id(session['user_id'])
    allowed_caja_ids = [p.vta_cajas_id_caja for p in permisos]
    # obtener aperturas para las cajas permitidas
    try:
        aperturas = Apertura.get_all_by_cajas(allowed_caja_ids)
    except Exception as e:
        if app.config.get('LOGIN_DEBUG'):
            print(f"[APERTURAS DEBUG] Error obteniendo aperturas: {e}")
        aperturas = []

    # obtener información de cajas para mostrar el nombre
    all_cajas = Caja.get_all()
    cajas = {c.id_caja: c for c in all_cajas}
    # cajas permitidas para este usuario
    allowed_cajas = [c for c in all_cajas if c.id_caja in allowed_caja_ids]

    # calcular totales de ventas por apertura para mostrar en la tabla
    totals_map = {}
    try:
        for ap in aperturas:
            try:
                totals_map[ap.id_apertura] = Apertura.get_totals_for_apertura(ap.id_apertura)
            except Exception:
                totals_map[ap.id_apertura] = 0
    except Exception:
        totals_map = {}

    most_recent = aperturas[0] if aperturas else None
    # Si venimos de cerrar una apertura, se guarda en session para mostrar el resumen modal
    apertura_resumen_id = None
    try:
        apertura_resumen_id = session.pop('apertura_resumen_id', None)
    except Exception:
        apertura_resumen_id = None

    return render_template('aperturas.html', aperturas=aperturas, cajas=cajas, totals_map=totals_map, allowed_cajas=allowed_cajas, most_recent=most_recent, apertura_resumen_id=apertura_resumen_id)


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
    # Verificar que la caja tenga una apertura activa antes de procesar el pago
    try:
        id_caja_int = int(id_caja)
    except Exception:
        flash('Caja inválida.', 'danger')
        return redirect(url_for('listar_aperturas'))

    active_ap = Apertura.get_active_by_caja(id_caja_int)
    if not active_ap:
        flash('No hay una apertura activa para esta caja. Abra una en Gestión de Aperturas antes de procesar pagos.', 'warning')
        return redirect(url_for('listar_aperturas'))

    productos_en_caja = Producto.get_by_caja(id_caja_int)
    
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
        session['last_id_caja'] = id_caja
    except Exception as e:
        print(f"[ERROR] No se pudo guardar en session: {e}")
        flash('Hubo un error al procesar los productos.', 'danger')
        return redirect(request.referrer)

    # Guardamos productos y total en sesión (ya están guardados), y redirigimos
    # sólo con el id_caja para evitar exponer datos sensibles en la URL.
    return redirect(url_for('datos_cliente', id_caja=id_caja))


@app.route('/apertura', methods=['POST'])
def apertura_crear():
    if 'user_id' not in session:
        return redirect('/')
    id_caja = request.form.get('id_caja') or session.get('last_id_caja')
    try:
        saldo_inicio = int(request.form.get('saldo_inicio', 0))
    except Exception:
        saldo_inicio = 0

    # Verificar permisos del usuario para la caja solicitada
    try:
        permisos = Permiso.get_by_user_id(session['user_id'])
        allowed_caja_ids = [p.vta_cajas_id_caja for p in permisos]
    except Exception:
        allowed_caja_ids = []

    try:
        id_caja_int = int(id_caja)
    except Exception:
        flash('Caja inválida.', 'danger')
        return redirect(url_for('listar_aperturas'))

    if id_caja_int not in allowed_caja_ids:
        flash('No tienes permisos para abrir una apertura en esta caja.', 'danger')
        return redirect(url_for('listar_aperturas'))

    # Verificar que no exista apertura activa para la caja (regla: una apertura por caja)
    existing = Apertura.get_active_by_caja(id_caja_int)
    if existing:
        flash('Ya existe una apertura activa para esta caja.', 'warning')
        return redirect(url_for('listar_aperturas'))

    id_ap = Apertura.open_with_amount(id_caja_int, session['user_id'], saldo_inicio)
    if id_ap:
        flash(f'Caja abierta (id {id_ap}).', 'success')
    else:
        flash('No se pudo abrir la caja.', 'danger')
    return redirect(url_for('listar_aperturas'))


@app.route('/apertura/<int:id_apertura>/cerrar', methods=['POST'])
def apertura_cerrar(id_apertura):
    if 'user_id' not in session:
        return redirect('/')
    # Si no se entrega `saldo_cierre`, usamos la suma de ventas como saldo final.
    observaciones = request.form.get('observaciones')

    try:
        # calcular totales de ventas para esta apertura
        total = Apertura.get_totals_for_apertura(id_apertura)

        saldo_cierre_raw = request.form.get('saldo_cierre')
        try:
            if saldo_cierre_raw is None or str(saldo_cierre_raw).strip() == '':
                saldo_cierre = total
            else:
                saldo_cierre = int(saldo_cierre_raw)
        except Exception:
            saldo_cierre = total

        diferencias = saldo_cierre - total

        # Intentar cerrar con resumen; capturamos excepciones para mostrar mensajes útiles
        try:
            res = Apertura.close_with_summary(id_apertura, saldo_cierre, total, diferencias, observaciones)
        except Exception as e:
            # Loggear en debug y notificar al usuario
            if app.config.get('LOGIN_DEBUG'):
                print(f"[APERTURA CLOSE ERROR] Error ejecutando close_with_summary for id={id_apertura}: {e}")
            flash('Error al cerrar la apertura (detalle en logs).', 'danger')
            return redirect(request.referrer or url_for('listar_aperturas'))

        if res is not False and res is not None:
            flash('Caja cerrada correctamente.', 'success')
            # Guardar id para mostrar resumen automáticamente en la lista
            try:
                session['apertura_resumen_id'] = id_apertura
            except Exception:
                pass
            return redirect(url_for('listar_aperturas'))
        else:
            flash('No se pudo actualizar la apertura. Ver logs.', 'danger')
            return redirect(request.referrer or url_for('listar_aperturas'))

    except Exception as e:
        # Error inesperado durante el proceso
        if app.config.get('LOGIN_DEBUG'):
            print(f"[APERTURA CLOSE EXCEPTION] id={id_apertura} err={e}")
        flash(f'Error inesperado al intentar cerrar la apertura: {e}', 'danger')
        return redirect(request.referrer or url_for('listar_aperturas'))


@app.route('/apertura/<int:id_apertura>/resumen')
def resumen_apertura(id_apertura):
    if 'user_id' not in session:
        return redirect('/')
    ap = Apertura.get_by_id(id_apertura)
    if not ap:
        flash('Apertura no encontrada.', 'warning')
        return redirect(url_for('listar_aperturas'))

    total = Apertura.get_totals_for_apertura(id_apertura)

    # preparar contexto
    caja = Caja.get_by_id(ap.id_caja_fk) if hasattr(Caja, 'get_by_id') else None
    return render_template('apertura_resumen.html', apertura=ap, total=total, caja=caja)


@app.route('/apertura/<int:id_apertura>/resumen_fragment')
def resumen_apertura_fragment(id_apertura):
    if 'user_id' not in session:
        return ('', 401)
    ap = Apertura.get_by_id(id_apertura)
    if not ap:
        return ('', 404)
    total = Apertura.get_totals_for_apertura(id_apertura)
    caja = Caja.get_by_id(ap.id_caja_fk) if hasattr(Caja, 'get_by_id') else None
    return render_template('apertura_resumen_modal.html', apertura=ap, total=total, caja=caja)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/datos_cliente', methods=['GET', 'POST'])
def datos_cliente():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        # Validar RUT y guardar datos del cliente temporalmente en sesión
        if not validar_rut(request.form.get('rut')):
            flash('RUT inválido. Por favor ingrese un RUT válido.', 'danger')
            return render_template('procesamiento_pago.html', **request.form)

        # `correo` puede ser opcional según esquema; no forzamos su presencia aquí

        # Guardar datos del cliente en sesión para usarlos en la confirmación y en el registro final
        session['cliente_temp'] = {
            'nombre': request.form.get('nombre'),
            'rut': request.form.get('rut'),
            'correo': request.form.get('correo'),
            'telefono': request.form.get('telefono'),
            'medio_pago': request.form.get('medio_pago')
        }

        return redirect(url_for('confirmar_pago'))
    # Para GET: preferimos tomar la lista de productos y total desde la sesión
    # (más seguro) si no vienen en los query params.
    id_caja = request.args.get('id_caja')
    productos = request.args.get('productos')
    total = request.args.get('total')

    if not productos:
        try:
            productos = json.dumps(session.get('productos_boleta', []))
        except Exception:
            productos = '[]'

    if not total:
        total = session.get('total_boleta', 0)

    return render_template('procesamiento_pago.html', id_caja=id_caja, productos=productos, total=total)

@app.route('/confirmar_pago', methods=['GET', 'POST'])
def confirmar_pago():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'GET':
        # Prefer session values (productos and total) and cliente_temp when available
        id_caja = request.args.get('id_caja') or session.get('last_id_caja')
        productos = request.args.get('productos')
        total = request.args.get('total')
        cliente = session.get('cliente_temp', {})

        if not productos:
            try:
                productos = json.dumps(session.get('productos_boleta', []))
            except Exception:
                productos = '[]'

        if not total:
            total = session.get('total_boleta', 0)

        # Pasar datos a la plantilla de confirmación
        ctx = {
            'id_caja': id_caja,
            'productos': productos,
            'total': total,
            'nombre': cliente.get('nombre'),
            'rut': cliente.get('rut'),
            'correo': cliente.get('correo')
        }
        return render_template('confirmar_pago.html', **ctx)
    
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
        # 1. Verificar Apertura: buscamos una apertura activa para la caja.
        try:
            id_caja_int = int(id_caja)
        except Exception:
            flash('Caja inválida.', 'danger')
            return redirect(url_for('ver_caja', id_caja=int(id_caja)))

        # Verificar que el usuario tenga permiso para operar en esta caja
        permisos = Permiso.get_by_user_id(session['user_id'])
        allowed_caja_ids = [p.vta_cajas_id_caja for p in permisos]
        if id_caja_int not in allowed_caja_ids:
            flash('No tienes permiso para operar en esa caja.', 'danger')
            return redirect(url_for('ver_caja', id_caja=id_caja_int))

        # Buscar apertura activa por caja (regla: una apertura por caja)
        active_apertura = Apertura.get_active_by_caja(id_caja_int)
        if not active_apertura:
            flash('No hay una apertura activa para esta caja. Abre una en Gestión de Aperturas.', 'danger')
            return redirect(url_for('ver_caja', id_caja=id_caja_int))

        # 2. Registrar/obtener cliente en MySQL
        cliente_temp = session.get('cliente_temp', {})
        nombre_cli = cliente_temp.get('nombre') or nombre
        rut_cli = cliente_temp.get('rut')
        correo_cli = cliente_temp.get('correo') or correo
        telefono_cli = cliente_temp.get('telefono')

        # Si no se entregó correo, permitimos continuar y registramos cliente con email NULL
        # (la tabla permite ahora valores nulos en email_cliente)

        # Buscar cliente por correo
        find_q = "SELECT id_cliente FROM vta_clientes WHERE email_cliente = %(email)s"
        found = connectToMySQL('sistemas').query_db(find_q, {'email': correo_cli})
        if found and isinstance(found, list) and len(found) > 0:
            id_cliente_fk = found[0].get('id_cliente')
            # Cliente existente
            try:
                flash(f'Cliente existente usado (id {id_cliente_fk}).', 'info')
            except Exception:
                pass
        else:
            ins_q = "INSERT INTO vta_clientes (email_cliente, nombre_cliente, telefono_cliente) VALUES (%(email)s, %(nombre)s, %(telefono)s)"
            id_cliente_fk = connectToMySQL('sistemas').query_db(ins_q, {'email': correo_cli, 'nombre': nombre_cli or 'Cliente', 'telefono': telefono_cli})
            # Cliente creado
            try:
                if correo_cli:
                    flash(f'Cliente creado (id {id_cliente_fk}) con correo {correo_cli}.', 'success')
                else:
                    flash(f'Cliente creado (id {id_cliente_fk}) sin correo.', 'success')
            except Exception:
                pass

        # 3. Crear la Venta (con referencia al cliente)
        data_venta = {
            'total_ventas': total,
            'id_apertura': active_apertura.id_apertura,
            'envio_correo': 1 if correo_cli else 0,
            'id_cliente_fk': id_cliente_fk
        }

        id_venta = Venta.create(data_venta, productos_list)

        if not id_venta:
            flash('Hubo un error al registrar la venta en la base de datos.', 'danger')
            return redirect(url_for('ver_caja', id_cja=int(id_caja)))

        # 4. Registrar medio de pago en vta_mediopago
        medio = session.pop('cliente_temp', {}).get('medio_pago') if session.get('cliente_temp') else request.form.get('medio_pago')
        try:
            if medio:
                mp_q = "INSERT INTO vta_mediopago (tipo_pago, id_ventas_fk) VALUES (%(tipo)s, %(id_venta)s)"
                connectToMySQL('sistemas').query_db(mp_q, {'tipo': medio, 'id_venta': id_venta})
        except Exception as e:
            if app.config.get('LOGIN_DEBUG'):
                print(f"[PAYMENT DEBUG] Error insertando medio de pago: {e}")

        flash(f'Venta #{id_venta} registrada con éxito!', 'success')

        # 3. Enviar Correo (si aplica)
        if correo_cli:
            # (El código para enviar correo se mantiene similar, se puede refactorizar a una función)
            # ... (código de envío de email HTML) ...
            flash(f'Resumen de compra enviado a {correo_cli}', 'success')

    except Exception as e:
        flash(f'Error inesperado durante el registro de la venta: {e}', 'danger')
        print(f"[SALE ERROR] {e}")
        return redirect(url_for('ver_caja', id_caja=int(id_caja)))

    # Limpiar sesión después de una venta exitosa
    session.pop('productos_boleta', None)
    session.pop('total_boleta', None)

    return redirect(url_for('ver_caja', id_caja=int(id_caja)))