from flask import Flask
import os
from pathlib import Path

# Cargar .env en desarrollo usando python-dotenv si está disponible
try:
	from dotenv import load_dotenv
	# Carga .env desde la raíz del proyecto (un nivel arriba de flask_app)
	base_dir = Path(__file__).resolve().parent.parent
	dotenv_path = base_dir / '.env'
	load_dotenv(dotenv_path)
except Exception:
	# Si python-dotenv no está instalado o .env no existe, continuamos usando os.environ
	pass

app = Flask(__name__)

# Secret key (mejor almacenarla en .env o variable de entorno en producción)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', "Llave muy secreta")

# Flag para activar logs de diagnóstico de login sin cambiar código en rutas.
app.config['LOGIN_DEBUG'] = os.environ.get('LOGIN_DEBUG', '0') == '1'

# Configuración de correo (se puede establecer en .env)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 25) or 25)
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', '0') == '1'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', '0') == '1'
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', f"no-reply@{app.config['MAIL_SERVER']}")


@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%d-%m-%Y %H:%M'):
	"""Format a datetime or string to a readable format for templates.
	If value is a string, attempt to parse common ISO formats; if parsing fails, return the original string.
	"""
	if not value:
		return '-'
	# If it's already a datetime
	try:
		from datetime import datetime
		if isinstance(value, datetime):
			return value.strftime(fmt)
	except Exception:
		pass
	# Try parsing ISO-like strings without external deps
	try:
		from datetime import datetime
		# Try direct ISO parsing
		try:
			dt = datetime.fromisoformat(value)
			return dt.strftime(fmt)
		except Exception:
			pass
		# Try common formats
		for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
			try:
				dt = datetime.strptime(value, f)
				return dt.strftime(fmt)
			except Exception:
				continue
	except Exception:
		pass
	# fallback: return original value as string
	try:
		return str(value)
	except Exception:
		return '-'