from flask_app.config.conexiones import connectToMySQL

class Permiso:
    def __init__(self, data):
        self.id_permiso = data['id_permiso']
        self.detalle_permiso = data['detalle_permiso']
        self.id_usuario_fk = data['id_usuario_fk']
        self.vta_cajas_id_caja = data['vta_cajas_id_caja']

    @classmethod
    def get_by_user_id(cls, user_id):
        query = "SELECT * FROM vta_permiso_usuarios WHERE id_usuario_fk = %(user_id)s;"
        data = {'user_id': user_id}
        results = connectToMySQL('sistemas').query_db(query, data)
        permisos = []
        if results:
            for row in results:
                permisos.append(cls(row))
        return permisos
