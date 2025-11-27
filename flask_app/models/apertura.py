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
        # Campos opcionales que pueden no existir en versiones antiguas de la tabla
        # (por eso usamos .get para evitar KeyError si la columna falta)
        self.saldo_inicio = data.get('saldo_inicio') if isinstance(data, dict) else None
        self.saldo_cierre = data.get('saldo_cierre') if isinstance(data, dict) else None
        self.total_ventas = data.get('total_ventas') if isinstance(data, dict) else None
        self.diferencias = data.get('diferencias') if isinstance(data, dict) else None
        self.observaciones = data.get('observaciones') if isinstance(data, dict) else None

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

    @classmethod
    def open_with_amount(cls, id_caja, id_usuario, saldo_inicio=0):
        query = "INSERT INTO vta_apertura (id_caja_fk, id_usuario_fk, estado_apertura, fecha_inicio_apertura, fecha_termino_apertura) VALUES (%(id_caja)s, %(id_usuario)s, 1, %(fecha_inicio)s, NULL);"
        data = {'id_caja': id_caja, 'id_usuario': id_usuario, 'fecha_inicio': datetime.now()}
        id_ap = connectToMySQL('sistemas').query_db(query, data)
        # si la columna saldo_inicio existe, actualizarla
        try:
            upd = "UPDATE vta_apertura SET saldo_inicio = %(saldo_inicio)s WHERE id_apertura = %(id_apertura)s"
            connectToMySQL('sistemas').query_db(upd, {'saldo_inicio': saldo_inicio, 'id_apertura': id_ap})
        except Exception:
            # columna no existe o error, ignorar
            pass
        return id_ap

    @classmethod
    def close_with_summary(cls, id_apertura, saldo_cierre, total_ventas, diferencias, observaciones=None):
        # Intentar actualizar con todos los campos; si la tabla aún no tiene
        # las columnas opcionales (saldo_cierre, diferencias, etc.) la consulta
        # fallará. En ese caso hacemos un fallback que solamente cierra la apertura
        # (marca estado_apertura = 0 y fecha_termino_apertura).
        query_full = """
            UPDATE vta_apertura SET estado_apertura = 0, fecha_termino_apertura = %(fecha_termino)s,
            saldo_cierre = %(saldo_cierre)s, total_ventas = %(total_ventas)s, diferencias = %(diferencias)s, observaciones = %(observaciones)s
            WHERE id_apertura = %(id_apertura)s;
        """
        data = {
            'fecha_termino': datetime.now(), 'saldo_cierre': saldo_cierre,
            'total_ventas': total_ventas, 'diferencias': diferencias,
            'observaciones': observaciones, 'id_apertura': id_apertura
        }
        # Ejecutar la consulta completa primero. connectToMySQL.query_db atrapa
        # excepciones y devuelve False en caso de error, por lo que comprobamos
        # el resultado en lugar de depender de except.
        res_full = connectToMySQL('sistemas').query_db(query_full, data)
        if res_full is not False:
            return res_full

        # Fallback: realizar una actualización mínima que sólo cierra la apertura
        fallback = "UPDATE vta_apertura SET estado_apertura = 0, fecha_termino_apertura = %(fecha_termino)s WHERE id_apertura = %(id_apertura)s;"
        res_fb = connectToMySQL('sistemas').query_db(fallback, {'fecha_termino': datetime.now(), 'id_apertura': id_apertura})
        return res_fb

    @classmethod
    def get_active_by_caja(cls, id_caja):
        query = "SELECT * FROM vta_apertura WHERE id_caja_fk = %(id_caja)s AND estado_apertura = 1 LIMIT 1;"
        res = connectToMySQL('sistemas').query_db(query, {'id_caja': id_caja})
        if not res:
            return None
        return cls(res[0])

    @classmethod
    def get_totals_for_apertura(cls, id_apertura):
        query = "SELECT IFNULL(SUM(total_ventas),0) AS total FROM vta_ventas WHERE id_apertura = %(id_apertura)s"
        res = connectToMySQL('sistemas').query_db(query, {'id_apertura': id_apertura})
        if not res:
            return 0
        return res[0].get('total', 0)

    @classmethod
    def get_all_by_cajas(cls, caja_ids):
        """
        Devuelve todas las aperturas para las cajas listadas en `caja_ids`.
        `caja_ids` debe ser una lista de ids de caja. Si está vacía, devuelve lista vacía.
        """
        if not caja_ids:
            return []
        # Sanitizar y construir lista para el IN
        placeholders = ','.join(['%s'] * len(caja_ids))
        query = f"SELECT * FROM vta_apertura WHERE id_caja_fk IN ({placeholders}) ORDER BY fecha_inicio_apertura DESC;"
        # connectToMySQL.query_db espera un dict en otros casos, pero aquí pasamos tuple/list
        res = connectToMySQL('sistemas').query_db(query, tuple(caja_ids))
        if not res:
            return []
        return [cls(r) for r in res]

    @classmethod
    def get_by_id(cls, id_apertura):
        query = "SELECT * FROM vta_apertura WHERE id_apertura = %(id_apertura)s LIMIT 1;"
        res = connectToMySQL('sistemas').query_db(query, {'id_apertura': id_apertura})
        if not res:
            return None
        return cls(res[0])

    @classmethod
    def get_active_global(cls):
        """Devuelve la apertura activa en todo el sistema (si existe)."""
        query = "SELECT * FROM vta_apertura WHERE estado_apertura = 1 LIMIT 1;"
        res = connectToMySQL('sistemas').query_db(query)
        if not res:
            return None
        return cls(res[0])
