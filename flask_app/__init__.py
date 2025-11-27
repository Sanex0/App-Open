from flask import Flask
import os

app = Flask(__name__)

# Secret key (consider moving to env var in production)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', "Llave muy secreta")

# Flag para activar logs de diagnóstico de login sin cambiar código en rutas.
# Para activarlo, exporta la variable de entorno LOGIN_DEBUG=1 antes de iniciar la app.
app.config['LOGIN_DEBUG'] = os.environ.get('LOGIN_DEBUG', '0') == '1'