from flask_app.config.conexiones import connectToMySQL
from datetime import datetime

class Apertura:
    def __init__(self, data):
        self.id_apertura = data['id_apertura']
        self.estado_apertura = data['estado_apertura']
        self.fecha_inicio_apertura = data['fecha_inicio_apertura']
        self.fecha_termino_apertura = data['fecha_termino_apertura']
        self.id_caja_fk = data['id_caja_fk']
        self.id_usuario_fk = data['id_usuario_fk']

    @classmethod
    def create(cls, data):
        query = "INSERT INTO vta_apertura (id_caja_fk, id_usuario_fk) VALUES (%(id_caja_fk)s, %(id_usuario_fk)s);"
        return connectToMySQL('sistemas').query_db(query, data)

    @classmethod
    def get_active_by_user_and_caja(cls, id_usuario, id_caja):
        query = "SELECT * FROM vta_apertura WHERE id_usuario_fk = %(id_usuario)s AND id_caja_fk = %(id_caja)s AND estado_apertura = 1;"
        data = {'id_usuario': id_usuario, 'id_caja': id_caja}
        result = connectToMySQL('sistemas').query_db(query, data)
        if not result:
            return None
        return cls(result[0])

    @classmethod
    def close(cls, id_apertura):
        query = "UPDATE vta_apertura SET estado_apertura = 0, fecha_termino_apertura = %(fecha_termino)s WHERE id_apertura = %(id_apertura)s;"
        data = {'id_apertura': id_apertura, 'fecha_termino': datetime.now()}
        return connectToMySQL('sistemas').query_db(query, data)
