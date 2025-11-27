from flask_app.config.conexiones import connectToMySQL

class User:
    def __init__(self, data):
        self.id_usuario = data['id_usuario']
        self.email_usuario = data['email_usuario']
        self.nombre_usuario = data['nombre_usuario']
        self.password = data['clave_usuario']
        self.estado_usuario = data['estado_usuario']

    @classmethod
    def get_by_id(cls, user_id):
        query = "SELECT * FROM adrecrear_usuarios WHERE id_usuario = %(id_usuario)s;"
        data = {'id_usuario': user_id}
        result = connectToMySQL('sistemas').query_db(query, data)
        if not result:
            return None
        return cls(result[0])

    @classmethod
    def get_by_email(cls, data):
        query = "SELECT * FROM adrecrear_usuarios WHERE email_usuario = %(email_usuario)s;"
        result = connectToMySQL('sistemas').query_db(query, data)
        if not result:
            return None
        return cls(result[0])

