from flask_app import app
from flask_app.controllers import users_controller
# Crear la aplicación Flask
# Force reload
if __name__ == '__main__':
    import os
    # host='0.0.0.0' permite conexiones desde otros dispositivos
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', debug=debug_mode, port=5001)