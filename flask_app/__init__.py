from flask import Flask
import os

app = Flask(__name__)

# Secret key (consider moving to env var in production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', "Llave muy secreta")

# Flag para activar logs de diagnóstico de login sin cambiar código en rutas.
# Para activarlo, exporta la variable de entorno LOGIN_DEBUG=1 antes de iniciar la app.
app.config['LOGIN_DEBUG'] = os.environ.get('LOGIN_DEBUG', '0') == '1'


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