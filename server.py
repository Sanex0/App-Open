from flask_app import app
from flask_app.controllers import users_controller
# Crear la aplicación Flask

if __name__ == '__main__':
    # host='0.0.0.0' permite conexiones desde otros dispositivos
    app.run(host='0.0.0.0', debug=True, port=5001)