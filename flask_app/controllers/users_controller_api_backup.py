import smtplib
import json
import requests
import pprint
from decimal import Decimal
from email.message import EmailMessage
from datetime import datetime, date

from flask import Flask, render_template, redirect, request, session, flash, url_for
from flask_bcrypt import Bcrypt

# Asegúrate de que estas rutas sean correctas en tu proyecto
from flask_app import app
from flask_app.models.productos import Producto
from flask_app.models.users import User
from flask_app.models.cajas import Caja
from flask_app.config.conexiones import connectToMySQL

bcrypt = Bcrypt(app)

# --- Funciones Auxiliares ---

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def validar_rut(rut):
    if not rut: return False
    rut = rut.replace('.', '').replace('-', '').upper()
    if len(rut) < 8 or len(rut) > 9:
        return False
    cuerpo = rut[:-1]
    dv = rut[-1]
    if not cuerpo.isdigit():
        return False
    if not (dv.isdigit() or dv == 'K'):
        return False
    
    suma = 0
    multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = multiplo + 1 if multiplo < 7 else 2
    
    dv_esperado = 11 - (suma % 11)
    if dv_esperado == 11:
        dv_esperado = '0'
    elif dv_esperado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(dv_esperado)
    
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

    user = User.get_by_email({'EMAIL_USUARIO': request.form['email']})
    if not user:
        flash('E-mail no encontrado', 'inicio_sesion')
        return redirect('/')
    if not bcrypt.check_password_hash(user.password, request.form['password']):
        flash('Contraseña incorrecta', 'inicio_sesion')
        return redirect('/')
    session['user_id'] = user.id_usuario
    return redirect('/index.html')

@app.route('/index.html')
def index_html():
    if 'user_id' not in session:
        return redirect('/')
    cajas = Caja.get_all()
    user = User.get_by_id(session['user_id']) if hasattr(User, 'get_by_id') else None
    return render_template('index.html', user=user, cajas=cajas)

@app.route('/caja/<int:id_caja>')
def ver_caja(id_caja):
    if 'user_id' not in session:
        return redirect('/')
    if request.args.get('notificado') == '1':
        flash('No se envió boleta. Pago no procesado.', 'info')
    productos = Producto.get_by_caja(id_caja)
    cajas = Caja.get_all()
    return render_template('caja.html', productos=productos, id_caja=id_caja, cajas=cajas)

@app.route('/pago', methods=['POST'])
def resumen_pago():
    if 'user_id' not in session:
        return redirect('/')
    
    productos_seleccionados = request.form.getlist('productos')
    if not productos_seleccionados:
        flash('No seleccionaste ningún producto.', 'pago')
        return redirect(request.referrer)
    
    id_caja = request.form.get('id_caja')
    productos = []
    total = 0
    
    productos_caja = Producto.get_by_caja(int(id_caja)) if id_caja and id_caja.isdigit() else []
    
    for prod in productos_caja:
        # Normalizar claves para evitar errores de mayusculas/minusculas
        p_id = str(prod.get('ID_PRODUCTO') or prod.get('id_producto'))
        
        if p_id in productos_seleccionados:
            cantidad = int(request.form.get(f'cantidad_{p_id}', 1))
            prod['cantidad'] = cantidad
            
            # Asegurar precio numérico
            precio = prod.get('PRECIO') or prod.get('precio') or 0
            subtotal = precio * cantidad
            total += subtotal
            productos.append(prod)
    
    # Guardar en SESSION
    try:
        productos_limpios = json.loads(json.dumps(productos, default=decimal_default))
        session['productos_boleta'] = productos_limpios
        session['total_boleta'] = total
        print(f"[DEBUG] Productos guardados en SESSION: {len(productos_limpios)} items")
    except Exception as e:
        print(f"[ERROR] No se pudo guardar en session: {e}")

    productos_json = json.dumps(productos, default=decimal_default)
    return render_template('resumen_pago.html', productos=productos, productos_json=productos_json, total=total, id_caja=id_caja)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/datos_cliente', methods=['GET', 'POST'])
def datos_cliente():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        rut = request.form.get('rut')
        correo = request.form.get('correo')
        id_caja = request.form.get('id_caja')
        # Ya no dependemos estrictamente de esto, pero lo mantenemos por compatibilidad
        productos = request.form.get('productos')
        total = request.form.get('total')

        if isinstance(productos, list):
            productos = json.dumps(productos)

        if not validar_rut(rut):
            flash('RUT inválido. Por favor ingrese un RUT válido.', 'danger')
            return render_template('form_boleta.html', id_caja=id_caja, productos=productos, total=total, nombre=nombre, rut=rut)
        
        return redirect(url_for('confirmar_pago', id_caja=id_caja, productos=productos, total=total, nombre=nombre, rut=rut, correo=correo))
    
    id_caja = request.args.get('id_caja')
    productos = request.args.get('productos')
    total = request.args.get('total')
    return render_template('form_boleta.html', id_caja=id_caja, productos=productos, total=total)

@app.route('/confirmar_pago', methods=['GET', 'POST'])
def confirmar_pago():
    if request.method == 'GET':
        id_caja = request.args.get('id_caja')
        productos = request.args.get('productos')
        total = request.args.get('total')
        nombre = request.args.get('nombre')
        rut = request.args.get('rut')
        correo = request.args.get('correo')
        return render_template('confirmar_pago.html', id_caja=id_caja, productos=productos, total=total, nombre=nombre, rut=rut, correo=correo)
    
    else:
        # --- PROCESO POST ---
        id_caja = request.form.get('id_caja')
        productos_form = request.form.get('productos')
        
        total = request.form.get('total')
        if not total and 'total_boleta' in session:
            total = session['total_boleta']

        correo = request.form.get('correo')
        nombre = request.form.get('nombre')
        rut_input = request.form.get('rut')

        # 1. Limpieza de RUT
        rut_final = "66666666-6" 
        if rut_input:
            clean_rut = rut_input.replace('.', '').replace(' ', '').upper()
            if '-' in clean_rut:
                rut_final = clean_rut
            elif len(clean_rut) > 1:
                rut_final = f"{clean_rut[:-1]}-{clean_rut[-1]}"
            if "NAN" in rut_final:
                rut_final = "66666666-6"

        # 2. Recuperar lista de productos
        productos_list = []
        if 'productos_boleta' in session and session['productos_boleta']:
            productos_list = session['productos_boleta']
            print("[DEBUG] Usando lista de productos desde SESSION (Seguro)")
        elif productos_form:
            try:
                productos_list = json.loads(productos_form)
                print("[DEBUG] Usando lista de productos desde JSON Form")
            except Exception as e:
                print(f"[ERROR JSON] Falló parseo del form: {e}")
                productos_list = []

        if not productos_list:
            print("[ALERTA CRÍTICA] La lista de productos está vacía.")
            flash('Error: No se encontraron productos para boletear.', 'warning')
            
        items = []
        for idx, prod in enumerate(productos_list, 1):
            cantidad = float(prod.get("cantidad", 1))
            precio = float(prod.get("precio") or prod.get("PRECIO") or 0)
            prod_name = prod.get("nombre") or prod.get("NOMBRE") or prod.get("name") or prod.get("NAME") or "Item Sin Nombre"
            amount = precio * cantidad
            
            items.append({
                "line": str(idx),
                "name": str(prod_name)[:40],
                "quantity": str(int(cantidad)),
                "price": str(int(precio)),
                "amount": str(int(amount))
            })

        total_str = str(int(float(total))) if total else "0"

        # 3. Construir JSON para Factura-X
        now = datetime.now()
        
        test_json = {
            "document_type": "CL39", 
            "test": True, 
            "numbering": False, #El true es para produccion
            "document": {
                "number": "5001",# Se quita al poner numbering en True
                "currency": "CLP",
                "issued_date": now.strftime("%Y-%m-%d"),
                "issued_date_time": now.strftime("%Y-%m-%dT%H:%M:%S"),
                "paymentTermsDescription": "CONTADO",
                "service_type": "3",
                "supplier": {
                    "tax_id": "99522880-7", 
                    "name": "ALIMENTAR SA",
                    "address": "AV QUILIN 1561",
                    "municipality": "QUILIN",
                    "city": "SANTIAGO"
                },
                "customer": {
                    "tax_id": rut_final,
                    "name": nombre,
                    "activity": "COMERCIAL",
                    "contactEmail": correo if correo else "",
                    "contactPhone": "", 
                    "address": "",
                    "municipality": "",
                    "city": ""
                },
                "amount": {
                    "net": total_str,
                    "exempt": "0",
                    "vat_rate": "19.00",
                    "vat": "0",
                    "total": total_str
                },
                "taxes": [], 
                "items": items
            },
            "custom": {
                "Observaciones": "VENTA BOLETA",
                "MntTotalWords": "" 
            }
        }

        print("[DEBUG] JSON a enviar:")
        pprint.pprint(test_json)

        # 4. Configuración API
        API_URL = "https://services.factura-x.com/generation/cl/39" 
        
        # --- DATOS REALES ---
        API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3OTUyNjI0MDAsImlhdCI6MTc2MzczOTM4MiwianRpIjoiNlpVRWNwa3hkYVBTZDhjbkR1R3RLdyIsInVzZXJfaWQiOjMzLCJjb20uYXh0ZXJvaWQuaXNfc3RhZmYiOmZhbHNlLCJjb20uYXh0ZXJvaWQud29ya3NwYWNlcyI6eyJhY2NfTmNJTVBWa3FybTFnc1A2NkVRIjoiOTY4ODI3NTAtMiIsImFjY181b0p0aUt2NldrNkN0UUx4dzciOiI5OTUyMjg4MC03IiwiYWNjX0xjbnlKWWpNTFJ4S2FUYmVmdyI6Ijc4ODYxMjAwLTEifSwiY29tLmF4dGVyb2lkLmFsbG93ZWRfaW50ZXJ2YWwiOjEwMDB9.eoVYS5KqiQyGGtbsMc3kNMreuB0Cnoz8HImNmcxQUZY" 
        WORKSPACE_ID = "acc_5oJtiKv6Wk6CtQLxw7"

        headers = {
            'Authorization': f"Bearer {API_TOKEN}", 
            'x-ax-workspace': WORKSPACE_ID,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(API_URL, json=test_json, headers=headers, timeout=15)
            
            print(f"[API STATUS] {response.status_code}")
            print(f"[API RESPONSE] {response.text}")

            if response.status_code == 200 or response.status_code == 201:
                api_data = response.json()
                
                pdf_link = None
                doc_id = None

                if 'id' in api_data:
                    doc_id = api_data['id']
                elif 'document' in api_data and 'id' in api_data['document']:
                    doc_id = api_data['document']['id']
                
                if 'document' in api_data and 'pdf_plot' in api_data['document']:
                    pdf_link = api_data['document']['pdf_plot']
                
                if not pdf_link and doc_id:
                    pdf_link = f"https://services.factura-x.com/documents/{doc_id}?format=pdf"
                    print(f"[DEBUG] URL PDF construida manualmente: {pdf_link}")

                if pdf_link:
                    flash('¡Pago confirmado y boleta generada!', 'success')
                    
                    if correo:
                        try:
                            # Descargar PDF a memoria (RAM)
                            # OJO: Esta llamada puede necesitar autenticación dependiendo de si el link es público o no
                            # Si el link es de 'services.factura-x.com', usamos los headers
                            download_headers = headers if "services.factura-x.com" in pdf_link else {}
                            
                            pdf_response = requests.get(pdf_link, headers=download_headers, timeout=15)
                            
                            if pdf_response.status_code == 200:
                                pdf_content = pdf_response.content # Contenido en bytes

                                msg = EmailMessage()
                                msg['Subject'] = 'Boleta Electrónica Club Recrear'
                                msg['From'] = 'no-reply@clubrecrear.cl'
                                msg['To'] = correo
                                msg.set_content(f'Estimado/a {nombre},\n\nAdjuntamos su boleta electrónica.\n\nGracias por su compra.')
                                
                                # Adjuntar directamente desde memoria
                                msg.add_attachment(pdf_content, maintype='application', subtype='pdf', filename=f"boleta_{rut_final}.pdf")

                                with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                                    smtp.starttls()
                                    smtp.login('michigato0405@gmail.com', 'fdir lsmj argz rrrv')
                                    smtp.send_message(msg)
                                
                                flash(f'Boleta enviada a {correo}', 'success')
                            else:
                                print(f"[PDF ERROR] Status: {pdf_response.status_code}, Body: {pdf_response.text}")
                                flash('Error al descargar el PDF desde Factura-X.', 'warning')
                        except Exception as e:
                            flash(f'Error enviando correo: {str(e)}', 'warning')
                            print(f"[MAIL ERROR] {e}")
                    else:
                        flash('Pago exitoso (Cliente sin correo).', 'success')
                else:
                    flash('Pago exitoso, pero la API no devolvió ID ni PDF.', 'warning')
            else:
                error_msg = response.text
                try:
                    error_json = response.json()
                    if 'message' in error_json:
                        error_msg = error_json['message']
                        
                        # Manejo específico para error de folios agotados
                        if "No available numbering" in error_msg:
                            error_msg = "Error Crítico: Se han agotado los folios de boletas disponibles en el sistema de facturación. Contacte al administrador."
                except:
                    pass
                flash(f'Error al emitir boleta: {error_msg}', 'danger')

        except requests.exceptions.Timeout:
            flash('Error: La API tardó demasiado.', 'danger')
        except requests.exceptions.ConnectionError:
            flash('Error: No se pudo conectar con el servidor.', 'danger')
        except Exception as e:
            flash(f'Error inesperado: {str(e)}', 'danger')
            print(f"[ERROR] {e}")

        # Limpiar sesión después de éxito (opcional)
        # session.pop('productos_boleta', None)

        return redirect(url_for('ver_caja', id_caja=int(id_caja)))
