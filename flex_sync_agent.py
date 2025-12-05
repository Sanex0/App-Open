"""
Agente de Sincronización con Factura X
Script independiente para sincronizar ventas con la API de Factura X

Uso:
    python flex_sync_agent.py --dry-run                    # Ver ventas pendientes
    python flex_sync_agent.py                               # Procesar todas las ventas
    python flex_sync_agent.py --limit 5 --delay 2          # Procesar 5 ventas con delay
"""

import requests
import time
import logging
import argparse
import sys
import pymysql.cursors
import pyodbc
import os
import smtplib
import random
from email.message import EmailMessage
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================

class MySQLConnection:
    """Conexión a MySQL para la base de datos de sistemas"""
    
    def __init__(self, db='sistemas'):
        try:
            self.connection = pymysql.connect(
                host=os.environ.get('DB_HOST', '181.212.204.13'),
                port=int(os.environ.get('DB_PORT', 3306)),
                user=os.environ.get('DB_USER', 'sistemasu'),
                password=os.environ.get('DB_PASSWORD', '5rTF422.3E'),
                db=db,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.connection.autocommit(True)
            logger.info(f"Conexión a base de datos '{db}' establecida")
        except Exception as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            raise

    def query_db(self, query, data=None):
        """Ejecutar query en la base de datos"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, data) if data else cursor.execute(query)
                
                if query.strip().lower().startswith("insert"):
                    self.connection.commit()
                    return cursor.lastrowid
                elif query.strip().lower().startswith("select"):
                    return cursor.fetchall()
                else:
                    self.connection.commit()
                    return True
        except Exception as e:
            logger.error(f"Error en query: {e}")
            if query.strip().lower().startswith("select"):
                return []
            return False
    
    def close(self):
        """Cerrar conexión"""
        if self.connection:
            self.connection.close()
            logger.info("Conexión a base de datos cerrada")


class SQLServerConnection:
    """Conexión a SQL Server para la base de datos de Flex"""
    
    def __init__(self, db='BDFlexline', user='flexline', password='flexline'):
        try:
            connection_str = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=192.168.1.150,1433;"
                f"DATABASE={db};"
                f"UID={user};"
                f"PWD={password};"
            )
            self.connection = pyodbc.connect(connection_str)
            logger.info(f"Conexión a SQL Server '{db}' establecida")
        except Exception as e:
            logger.error(f"Error al conectar a SQL Server: {e}")
            raise
    
    def query_db(self, query, data=None):
        """Ejecutar query en SQL Server"""
        cursor = self.connection.cursor()
        try:
            if data:
                cursor.execute(query, data)
            else:
                cursor.execute(query)
            
            if query.strip().lower().startswith("select"):
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            elif query.strip().lower().startswith("insert"):
                self.connection.commit()
                return cursor.lastrowid
            else:
                self.connection.commit()
                return True
        except Exception as e:
            logger.error(f"Error en query SQL Server: {e}")
            if query.strip().lower().startswith("select"):
                return []
            return False
        finally:
            cursor.close()
    
    def close(self):
        """Cerrar conexión"""
        if self.connection:
            self.connection.close()
            logger.info("Conexión a SQL Server cerrada")


# ============================================================================
# AGENTE DE SINCRONIZACIÓN
# ============================================================================

class FlexSyncAgent:
    """Agente para sincronizar ventas con la API de Factura X"""
    
    # URL y configuración de la API de Factura X
    FACTURA_X_API_URL = "https://services.factura-x.com/generation/cl/39"
    FACTURA_X_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3OTUyNjI0MDAsImlhdCI6MTc2MzczOTM4MiwianRpIjoiNlpVRWNwa3hkYVBTZDhjbkR1R3RLdyIsInVzZXJfaWQiOjMzLCJjb20uYXh0ZXJvaWQuaXNfc3RhZmYiOmZhbHNlLCJjb20uYXh0ZXJvaWQud29ya3NwYWNlcyI6eyJhY2NfTmNJTVBWa3FybTFnc1A2NkVRIjoiOTY4ODI3NTAtMiIsImFjY181b0p0aUt2NldrNkN0UUx4dzciOiI5OTUyMjg4MC03IiwiYWNjX0xjbnlKWWpNTFJ4S2FUYmVmdyI6Ijc4ODYxMjAwLTEifSwiY29tLmF4dGVyb2lkLmFsbG93ZWRfaW50ZXJ2YWwiOjEwMDB9.eoVYS5KqiQyGGtbsMc3kNMreuB0Cnoz8HImNmcxQUZY"
    WORKSPACE_ID = "acc_5oJtiKv6Wk6CtQLxw7"
    
    # Configuración SMTP - Múltiples cuentas para balanceo (cPanel)
    SMTP_SERVER = 'mail.clubrecrear.cl'
    SMTP_PORT = 465
    SMTP_USERS = [
        "no-responder@clubrecrear.cl",
        "no-responder1@clubrecrear.cl",
        "no-responder2@clubrecrear.cl"
    ]
    SMTP_PASSWORDS = [
        "++&x,TyMji!;",
        "L7MVjISZvw1t",
        "3RJC^Of(L_t}"
    ]
    
    def __init__(self, api_key=None, workspace_id=None, test_mode=False):
        """
        Inicializar el agente de sincronización
        
        Args:
            api_key (str, optional): API key de Factura X
            workspace_id (str, optional): Workspace ID de Factura X
            test_mode (bool, optional): Si es True, las boletas serán de prueba (default: False = Producción)
        """
        self.api_key = api_key or os.environ.get('FACTURA_X_API_KEY') or self.FACTURA_X_API_TOKEN
        self.workspace_id = workspace_id or os.environ.get('FACTURA_X_WORKSPACE_ID') or self.WORKSPACE_ID
        self.smtp_server = os.environ.get('SMTP_SERVER') or self.SMTP_SERVER
        self.smtp_port = int(os.environ.get('SMTP_PORT') or self.SMTP_PORT)
        self.test_mode = test_mode or os.environ.get('FACTURA_X_TEST_MODE', '').lower() == 'true'
        self.db = MySQLConnection('sistemas')
        self.db_flex = SQLServerConnection('BDFlexline', 'flexline', 'flexline')
        
        if not self.api_key:
            logger.warning("No se proporcionó API key de Factura X")
        
        if self.test_mode:
            logger.warning("⚠️  MODO PRUEBA ACTIVADO - Las boletas serán de PRUEBA")
        else:
            logger.info("✓ MODO PRODUCCIÓN - Las boletas serán REALES")
    
    def get_random_smtp_credentials(self):
        """
        Obtener credenciales SMTP aleatorias para balanceo de carga
        Cada correo usa su contraseña correspondiente según el índice
        
        Returns:
            tuple: (smtp_user, smtp_password)
        """
        indice = random.randint(0, len(self.SMTP_USERS) - 1)
        return self.SMTP_USERS[indice], self.SMTP_PASSWORDS[indice]
        
    def get_pending_ventas(self):
        """
        Obtener ventas pendientes de envío a Factura X (envio_flex = 1)
        
        Returns:
            list: Lista de ventas pendientes
        """
        query = """
            SELECT 
                id_ventas,
                total_ventas,
                fecha_venta,
                id_correlativo_flex,
                id_apertura,
                id_cliente_fk,
                id_fx
            FROM vta_ventas
            WHERE envio_flex = 1 
                AND (id_fx IS NULL OR id_fx = '')
                AND id_correlativo_flex IS NOT NULL 
                AND id_correlativo_flex > 0
            ORDER BY id_ventas ASC
        """
        
        try:
            ventas = self.db.query_db(query)
            logger.info(f"Se encontraron {len(ventas)} ventas pendientes de envío")
            return ventas
        except Exception as e:
            logger.error(f"Error al obtener ventas pendientes: {e}")
            return []
    
    def get_venta_detalle(self, id_venta):
        """
        Obtener el detalle de una venta y buscar nombres de productos en Flex
        
        Args:
            id_venta (int): ID de la venta
            
        Returns:
            list: Lista de detalles de la venta con nombres de productos de Flex
        """
        query = """
            SELECT 
                dv.id_detalle_ventas,
                dv.id_listaprecio,
                dv.cantidad,
                dv.id_producto_fk,
                p.descripcion_prod,
                CAST(dv.id_listaprecio AS UNSIGNED) as precio_unitario
            FROM vta_detalle_ventas dv
            INNER JOIN vta_productos p ON dv.id_producto_fk = p.id_prod
            WHERE dv.id_venta = %s
        """
        
        try:
            detalle = self.db.query_db(query, (id_venta,))
            
            # Para cada item, buscar el nombre del producto en Flex
            for item in detalle:
                codigo_producto = item.get('descripcion_prod')
                if codigo_producto:
                    # Buscar en la base de datos de Flex (SQL Server)
                    query_flex = "SELECT GLOSA FROM flexline.producto WHERE PRODUCTO = ?"
                    resultado = self.db_flex.query_db(query_flex, (codigo_producto,))
                    
                    if resultado and len(resultado) > 0:
                        item['nombre_producto_flex'] = resultado[0]['GLOSA']
                    else:
                        item['nombre_producto_flex'] = codigo_producto
                else:
                    item['nombre_producto_flex'] = 'Producto'
            
            return detalle
        except Exception as e:
            logger.error(f"Error al obtener detalle de venta {id_venta}: {e}")
            return []
    
    def get_cliente_info(self, id_cliente):
        """
        Obtener información del cliente
        
        Args:
            id_cliente (int): ID del cliente
            
        Returns:
            dict|None: Información del cliente o None
        """
        if not id_cliente:
            return None
            
        query = """
            SELECT 
                id_cliente,
                nombre_cliente,
                apellido_cliente,
                email_cliente,
                telefono_cliente
            FROM vta_clientes
            WHERE id_cliente = %s
        """
        
        try:
            clientes = self.db.query_db(query, (id_cliente,))
            return clientes[0] if clientes else None
        except Exception as e:
            logger.error(f"Error al obtener información del cliente {id_cliente}: {e}")
            return None
    
    def send_to_facturax_api(self, venta, detalle, cliente=None):
        """
        Enviar venta a la API de Factura X
        
        Args:
            venta (dict): Datos de la venta
            detalle (list): Detalle de la venta
            cliente (dict, optional): Información del cliente
            
        Returns:
            tuple: (doc_id, pdf_url) o (None, None) si falla
        """
        try:
            now_dt = venta['fecha_venta'] if isinstance(venta['fecha_venta'], datetime) else datetime.now()
            
            # Preparar RUT del cliente (siempre genérico)
            rut_final = "66666666-6"
            
            # Preparar items en el formato esperado por Factura X
            items_api = []
            for idx, item in enumerate(detalle, 1):
                cantidad = int(item['cantidad'])
                precio = int(item.get('precio_unitario') or item.get('id_listaprecio', 0))
                prod_name = str(item.get('nombre_producto_flex') or item['descripcion_prod'])[:40]
                amount = precio * cantidad
                
                items_api.append({
                    "line": str(idx),
                    "name": prod_name,
                    "quantity": str(cantidad),
                    "price": str(precio),
                    "amount": str(amount)
                })
            
            total_str = str(int(venta['total_ventas']))
            
            # Construir JSON en el formato exacto de Factura X
            factura_json = {
                "document_type": "CL39",
                "test": self.test_mode,  # False = Producción, True = Prueba
                "numbering": False,
                "document": {
                    "number": str(venta['id_correlativo_flex']),
                    "currency": "CLP",
                    "issued_date": now_dt.strftime("%Y-%m-%d"),
                    "issued_date_time": now_dt.strftime("%Y-%m-%dT%H:%M:%S"),
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
                        "name": (f"{cliente.get('nombre_cliente', '')} {cliente.get('apellido_cliente', '')}".strip() 
                                if cliente else "Cliente") or "Cliente",
                        "activity": "COMERCIAL",
                        "contactEmail": cliente.get('email_cliente', '') if cliente else "",
                        "contactPhone": cliente.get('telefono_cliente', '') if cliente else "",
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
                    "items": items_api
                },
                "custom": {
                    "Observaciones": "VENTA BOLETA",
                    "MntTotalWords": ""
                }
            }
            
            # Preparar headers
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'x-ax-workspace': self.workspace_id,
                'Content-Type': 'application/json'
            }
            
            # Enviar request a la API
            logger.info(f"Enviando venta {venta['id_ventas']} con number={venta['id_correlativo_flex']} a Factura X")
            logger.debug(f"Payload: {factura_json}")
            
            response = requests.post(
                self.FACTURA_X_API_URL,
                json=factura_json,
                headers=headers,
                timeout=15
            )
            
            # Verificar respuesta
            if response.status_code in [200, 201]:
                api_data = response.json()
                
                # Extraer el ID del documento y PDF
                doc_id = None
                pdf_url = None
                
                if 'id' in api_data:
                    doc_id = api_data['id']
                elif 'document' in api_data and 'id' in api_data['document']:
                    doc_id = api_data['document']['id']
                
                # Buscar URL del PDF
                if 'document' in api_data and 'pdf_plot' in api_data['document']:
                    pdf_url = api_data['document']['pdf_plot']
                
                # Si no hay URL de PDF pero tenemos ID, construir URL
                if not pdf_url and doc_id:
                    pdf_url = f"https://services.factura-x.com/documents/{doc_id}?format=pdf"
                
                if doc_id:
                    logger.info(f"✓ Venta {venta['id_ventas']} enviada exitosamente. ID Factura X: {doc_id}")
                    if pdf_url:
                        logger.info(f"  PDF URL: {pdf_url}")
                    return str(doc_id), pdf_url
                else:
                    logger.error(f"✗ La API retornó sin ID para venta {venta['id_ventas']}: {api_data}")
                    return None, None
            else:
                error_msg = response.text
                try:
                    error_json = response.json()
                    if 'message' in error_json:
                        error_msg = error_json['message']
                except:
                    pass
                logger.error(f"✗ Error en API para venta {venta['id_ventas']}: {response.status_code} - {error_msg}")
                return None, None
                
        except requests.exceptions.Timeout:
            logger.error(f"✗ Timeout al enviar venta {venta['id_ventas']} a la API")
            return None, None
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Error de conexión al enviar venta {venta['id_ventas']}: {e}")
            return None, None
        except Exception as e:
            logger.error(f"✗ Error inesperado al enviar venta {venta['id_ventas']}: {e}")
            return None, None
    
    def update_id_fx(self, id_venta, id_fx):
        """
        Actualizar el campo id_fx en la base de datos
        
        Args:
            id_venta (int): ID de la venta
            id_fx (str): ID retornado por la API de Factura X
            
        Returns:
            bool: True si se actualizó correctamente
        """
        query = """
            UPDATE vta_ventas
            SET id_fx = %s
            WHERE id_ventas = %s
        """
        
        try:
            result = self.db.query_db(query, (id_fx, id_venta))
            if result:
                logger.info(f"✓ ID Factura X '{id_fx}' guardado para venta {id_venta}")
                return True
            else:
                logger.error(f"✗ No se pudo actualizar id_fx para venta {id_venta}")
                return False
        except Exception as e:
            logger.error(f"✗ Error al actualizar id_fx para venta {id_venta}: {e}")
            return False
    
    def update_envio_fx(self, id_venta):
        """
        Actualizar el campo envio_fx a 1 después de enviar a la API
        
        Args:
            id_venta (int): ID de la venta
            
        Returns:
            bool: True si se actualizó correctamente
        """
        query = """
            UPDATE vta_ventas
            SET envio_fx = 1
            WHERE id_ventas = %s
        """
        
        try:
            result = self.db.query_db(query, (id_venta,))
            if result:
                logger.info(f"✓ envio_fx = 1 para venta {id_venta}")
                return True
            else:
                logger.error(f"✗ No se pudo actualizar envio_fx para venta {id_venta}")
                return False
        except Exception as e:
            logger.error(f"✗ Error al actualizar envio_fx para venta {id_venta}: {e}")
            return False
    
    def update_envio_correo(self, id_venta):
        """
        Actualizar el campo envio_correo a 1 después de enviar el correo
        
        Args:
            id_venta (int): ID de la venta
            
        Returns:
            bool: True si se actualizó correctamente
        """
        query = """
            UPDATE vta_ventas
            SET envio_correo = 1
            WHERE id_ventas = %s
        """
        
        try:
            result = self.db.query_db(query, (id_venta,))
            if result:
                logger.info(f"✓ envio_correo = 1 para venta {id_venta}")
                return True
            else:
                logger.error(f"✗ No se pudo actualizar envio_correo para venta {id_venta}")
                return False
        except Exception as e:
            logger.error(f"✗ Error al actualizar envio_correo para venta {id_venta}: {e}")
            return False
    
    def update_envio_boleta(self, id_venta):
        """
        Actualizar el campo envio_boleta a 1 después de enviar el correo
        
        Args:
            id_venta (int): ID de la venta
            
        Returns:
            bool: True si se actualizó correctamente
        """
        query = """
            UPDATE vta_ventas
            SET envio_boleta = 1
            WHERE id_ventas = %s
        """
        
        try:
            result = self.db.query_db(query, (id_venta,))
            if result:
                logger.info(f"✓ envio_boleta = 1 para venta {id_venta}")
                return True
            else:
                logger.error(f"✗ No se pudo actualizar envio_boleta para venta {id_venta}")
                return False
        except Exception as e:
            logger.error(f"✗ Error al actualizar envio_boleta para venta {id_venta}: {e}")
            return False
    
    def download_pdf(self, pdf_url):
        """
        Descargar el PDF desde la URL
        
        Args:
            pdf_url (str): URL del PDF
            
        Returns:
            bytes|None: Contenido del PDF o None si falla
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'x-ax-workspace': self.workspace_id
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"✓ PDF descargado exitosamente ({len(response.content)} bytes)")
                return response.content
            else:
                logger.error(f"✗ Error descargando PDF: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"✗ Error al descargar PDF: {e}")
            return None
    
    def send_email_with_pdf(self, venta, cliente, pdf_content, rut_final="66666666-6"):
        """
        Enviar correo con el PDF adjunto
        
        Args:
            venta (dict): Datos de la venta
            cliente (dict): Información del cliente
            pdf_content (bytes): Contenido del PDF
            rut_final (str): RUT formateado
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            correo = cliente.get('email_cliente')
            if not correo:
                logger.warning(f"✗ Venta {venta['id_ventas']} no tiene correo del cliente")
                return False
            
            # Preparar datos
            nombre_cliente = f"{cliente.get('nombre_cliente', '')} {cliente.get('apellido_cliente', '')}".strip() or "Cliente"
            fecha = venta['fecha_venta'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(venta['fecha_venta'], datetime) else str(venta['fecha_venta'])
            total = int(venta['total_ventas'])
            
            # Preparar contenido del correo
            subject = 'Comprobante de Venta Club Recrear OPEN DAY'
            
            saludo = f"Estimado/a Cliente"
            
            body = (
                f"{saludo},\n\n"
                f"Muchas gracias por su compra.\n\n"
                f"Adjunto encontrará su boleta electrónica N° {venta['id_correlativo_flex']} "
                f"por un total de ${total:,}.\n\n"
                f"Esperamos verle pronto.\n\n"
                f"Saludos cordiales,\n"
                f"Club Recrear"
            )
            
            # Obtener credenciales SMTP aleatorias (correo y su contraseña correspondiente)
            smtp_user, smtp_password = self.get_random_smtp_credentials()
            
            # Crear mensaje
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = smtp_user
            msg['To'] = correo
            msg.set_content(body)
            
            # Adjuntar PDF
            if pdf_content:
                msg.add_attachment(
                    pdf_content,
                    maintype='application',
                    subtype='pdf',
                    filename=f'boleta_{rut_final}.pdf'
                )
            
            # Enviar correo
            logger.info(f"Enviando correo a {correo} desde {smtp_user}...")
            
            # Puerto 465 usa SMTP_SSL, no SMTP con starttls
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as smtp:
                smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)
            
            logger.info(f"✓ Correo enviado exitosamente a {correo} desde {smtp_user}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error al enviar correo: {e}")
            return False
    
    def validate_and_send_email(self, venta, cliente, pdf_url, rut_final):
        """
        Validar que envio_fx y id_fx tengan datos, y enviar el PDF por correo
        
        Args:
            venta (dict): Datos de la venta
            cliente (dict): Información del cliente
            pdf_url (str): URL del PDF
            rut_final (str): RUT formateado
            
        Returns:
            bool: True si se envió el correo exitosamente
        """
        try:
            # Validar que tenga envio_fx y id_fx
            if not venta.get('envio_fx'):
                logger.warning(f"✗ Venta {venta['id_ventas']} no tiene envio_fx = 1")
                return False
            
            if not venta.get('id_fx'):
                logger.warning(f"✗ Venta {venta['id_ventas']} no tiene id_fx")
                return False
            
            # Verificar que tenga correo
            if not cliente or not cliente.get('email_cliente'):
                logger.info(f"⊘ Venta {venta['id_ventas']} no tiene correo, se omite envío")
                return False
            
            logger.info(f"Validación exitosa: envio_fx={venta.get('envio_fx')}, id_fx={venta.get('id_fx')}")
            
            # Descargar PDF
            pdf_content = self.download_pdf(pdf_url)
            if not pdf_content:
                logger.error(f"✗ No se pudo descargar el PDF para venta {venta['id_ventas']}")
                return False
            
            # Enviar correo
            return self.send_email_with_pdf(venta, cliente, pdf_content, rut_final)
            
        except Exception as e:
            logger.error(f"✗ Error en validate_and_send_email: {e}")
            return False
    
    def process_venta(self, venta):
        """
        Procesar una venta individual
        
        Args:
            venta (dict): Datos de la venta
            
        Returns:
            bool: True si se procesó correctamente
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Procesando venta {venta['id_ventas']}")
            logger.info(f"{'='*60}")
            
            # Obtener detalle
            detalle = self.get_venta_detalle(venta['id_ventas'])
            
            if not detalle:
                logger.warning(f"✗ Venta {venta['id_ventas']} no tiene detalles")
                return False
            
            logger.info(f"Detalle: {len(detalle)} items")
            
            # Obtener información del cliente si existe
            cliente = None
            rut_final = "66666666-6"
            
            if venta.get('id_cliente_fk'):
                cliente = self.get_cliente_info(venta['id_cliente_fk'])
                if cliente:
                    logger.info(f"Cliente: {cliente.get('nombre_cliente')} {cliente.get('apellido_cliente', '')}")
                    logger.info(f"Email: {cliente.get('email_cliente', 'Sin correo')}")
            
            # Enviar a API de Factura X
            logger.info("Paso 1: Enviando a API de Factura X...")
            id_fx, pdf_url = self.send_to_facturax_api(venta, detalle, cliente)
            
            if not id_fx:
                logger.error("✗ Falló el envío a la API")
                return False
            
            # Guardar ID en base de datos
            logger.info("Paso 2: Guardando id_fx en base de datos...")
            if not self.update_id_fx(venta['id_ventas'], id_fx):
                logger.error("✗ Falló guardar id_fx")
                return False
            
            # Marcar envio_fx = 1 porque se subió exitosamente a la API
            logger.info("Paso 3: Marcando envio_fx = 1...")
            self.update_envio_fx(venta['id_ventas'])
            
            # Actualizar venta con el id_fx para la validación
            venta['id_fx'] = id_fx
            venta['envio_fx'] = 1
            
            # Validar y enviar correo si corresponde
            logger.info("Paso 4: Validando y enviando correo...")
            if pdf_url and cliente and cliente.get('email_cliente'):
                email_sent = self.validate_and_send_email(venta, cliente, pdf_url, rut_final)
                
                if email_sent:
                    logger.info("Paso 5: Actualizando envio_correo = 1 y envio_boleta = 1...")
                    self.update_envio_correo(venta['id_ventas'])
                    self.update_envio_boleta(venta['id_ventas'])
                    logger.info("✓ Proceso completo exitoso (API + Email + Boleta)")
                else:
                    logger.warning("⊘ Proceso parcial exitoso (API OK, Email falló)")
            else:
                if not cliente or not cliente.get('email_cliente'):
                    logger.info("⊘ No se envió correo (sin email del cliente)")
                    # Marcar envio_correo = 1 y envio_boleta = 1 aunque no tenga correo
                    logger.info("Marcando envio_correo = 1 y envio_boleta = 1 (sin correo)")
                    self.update_envio_correo(venta['id_ventas'])
                    self.update_envio_boleta(venta['id_ventas'])
                else:
                    logger.warning("⊘ No se envió correo (sin PDF URL)")
                logger.info("✓ Proceso exitoso (API completado)")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error al procesar venta {venta['id_ventas']}: {e}")
            return False
    
    def run(self, limit=None, delay=0):
        """
        Ejecutar el agente para procesar ventas pendientes
        
        Args:
            limit (int, optional): Número máximo de ventas a procesar
            delay (int, optional): Segundos de espera entre cada venta
            
        Returns:
            dict: Estadísticas de procesamiento
        """
        logger.info("\n" + "="*80)
        logger.info("AGENTE DE SINCRONIZACIÓN CON FACTURA X")
        logger.info("="*80 + "\n")
        
        # Obtener ventas pendientes
        ventas = self.get_pending_ventas()
        
        if not ventas:
            logger.info("✓ No hay ventas pendientes de procesar")
            return {
                'total': 0,
                'exitosos': 0,
                'fallidos': 0
            }
        
        # Aplicar límite si se especifica
        if limit:
            ventas = ventas[:limit]
            logger.info(f"Procesando un máximo de {limit} ventas de {len(self.get_pending_ventas())} pendientes\n")
        else:
            logger.info(f"Procesando todas las ventas pendientes ({len(ventas)})\n")
        
        # Procesar ventas
        exitosos = 0
        fallidos = 0
        
        for i, venta in enumerate(ventas, 1):
            logger.info(f"[{i}/{len(ventas)}] Venta ID: {venta['id_ventas']} | Correlativo: {venta['id_correlativo_flex']} | Total: ${venta['total_ventas']}")
            
            success = self.process_venta(venta)
            
            if success:
                exitosos += 1
            else:
                fallidos += 1
            
            # Esperar entre requests si se especifica
            if delay > 0 and i < len(ventas):
                logger.info(f"Esperando {delay} segundos...")
                time.sleep(delay)
        
        # Estadísticas finales
        stats = {
            'total': len(ventas),
            'exitosos': exitosos,
            'fallidos': fallidos
        }
        
        logger.info("\n" + "="*80)
        logger.info("RESUMEN DE SINCRONIZACIÓN")
        logger.info("="*80)
        logger.info(f"Total procesadas:  {stats['total']}")
        logger.info(f"Exitosas:          {stats['exitosos']}")
        logger.info(f"Fallidas:          {stats['fallidos']}")
        
        if stats['total'] > 0:
            tasa = (stats['exitosos'] / stats['total']) * 100
            logger.info(f"Tasa de éxito:     {tasa:.1f}%")
        
        logger.info("="*80 + "\n")
        
        return stats
    
    def close(self):
        """Cerrar conexiones"""
        self.db.close()
        self.db_flex.close()


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def show_pending_ventas(agent):
    """Mostrar ventas pendientes sin procesarlas (dry-run)"""
    print("\n" + "="*80)
    print("VENTAS PENDIENTES DE SINCRONIZACIÓN")
    print("="*80 + "\n")
    
    ventas = agent.get_pending_ventas()
    
    if not ventas:
        print("✓ No hay ventas pendientes de procesar\n")
        return
    
    print(f"Se encontraron {len(ventas)} ventas pendientes:\n")
    
    for i, venta in enumerate(ventas, 1):
        print(f"{i}. Venta ID: {venta['id_ventas']}")
        print(f"   ├─ Total: ${venta['total_ventas']}")
        print(f"   ├─ Fecha: {venta['fecha_venta']}")
        print(f"   ├─ ID Correlativo Flex: {venta['id_correlativo_flex']}")
        print(f"   ├─ ID Apertura: {venta['id_apertura']}")
        print(f"   └─ ID Cliente: {venta['id_cliente_fk'] or 'N/A'}")
        print()
    
    print("="*80 + "\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Sincronizar ventas con la API de Factura X',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python flex_sync_agent.py --dry-run
  python flex_sync_agent.py --limit 10
  python flex_sync_agent.py --limit 5 --delay 2
  python flex_sync_agent.py --api-key "tu_api_key_aqui"

Variables de entorno opcionales:
  FACTURA_X_API_KEY    API Key de Factura X
  DB_HOST              Host de la base de datos (default: 181.212.204.13)
  DB_PORT              Puerto de la base de datos (default: 3306)
  DB_USER              Usuario de la base de datos (default: root)
  DB_PASSWORD          Contraseña de la base de datos
        """
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='API Key de Factura X (o usar variable FACTURA_X_API_KEY)'
    )
    
    parser.add_argument(
        '--workspace-id',
        type=str,
        default=None,
        help='Workspace ID de Factura X (o usar variable FACTURA_X_WORKSPACE_ID)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Número máximo de ventas a procesar (default: todas)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=1,
        help='Segundos de espera entre cada venta (default: 1)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostrar ventas pendientes sin procesarlas'
    )
    
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Modo de prueba (boletas de prueba, no reales)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mostrar logs detallados (DEBUG)'
    )
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Crear instancia del agente
    agent = None
    
    try:
        agent = FlexSyncAgent(
            api_key=args.api_key, 
            workspace_id=args.workspace_id,
            test_mode=args.test_mode
        )
        
        # Si es dry-run, solo mostrar ventas pendientes
        if args.dry_run:
            show_pending_ventas(agent)
            return 0
        
        # Ejecutar el agente
        stats = agent.run(limit=args.limit, delay=args.delay)
        
        # Retornar código de salida basado en resultados
        if stats['total'] == 0:
            return 0
        elif stats['exitosos'] == stats['total']:
            return 0
        elif stats['exitosos'] > 0:
            return 1  # Algunas fallaron
        else:
            return 2  # Todas fallaron
            
    except KeyboardInterrupt:
        logger.warning("\n\n✗ Proceso interrumpido por el usuario")
        return 130
        
    except Exception as e:
        logger.error(f"\n✗ Error fatal: {e}")
        return 1
        
    finally:
        if agent:
            agent.close()


if __name__ == "__main__":
    sys.exit(main())
