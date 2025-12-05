from flask_app.config.conexiones import connectToMySQL

class Caja:
    def __init__(self, data):
        self.id_caja = data['id_caja']
        self.detalle_caja = data['detalle_caja']
        self.es_variable = data.get('es_variable', 0)
        self.vta_club_id_club = data['vta_club_id_club']

    @classmethod
    def get_all(cls):
        query = "SELECT * FROM vta_cajas;"
        results = connectToMySQL('sistemas').query_db(query)
        cajas = []
        if results:
            for row in results:
                cajas.append(cls(row))
        return cajas

    @classmethod
    def get_by_id(cls, id_caja):
        query = "SELECT * FROM vta_cajas WHERE id_caja = %(id_caja)s LIMIT 1;"
        res = connectToMySQL('sistemas').query_db(query, {'id_caja': id_caja})
        if not res:
            return None
        return cls(res[0])
