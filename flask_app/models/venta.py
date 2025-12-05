from flask_app.config.conexiones import connectToMySQL

class Venta:
    def __init__(self, data):
        self.id_ventas = data['id_ventas']
        self.total_ventas = data['total_ventas']
        self.envio_flex = data['envio_flex']
        self.envio_fx = data['envio_fx']
        self.envio_correo = data['envio_correo']
        self.id_apertura = data['id_apertura']

    @classmethod
    def create(cls, data_venta, items):
        # Crear la venta principal
        # Se agregan campos nuevos: id_correlativo_flex (NOT NULL) y envio_boleta
        # Si no vienen en data_venta, se asumen valores por defecto (0)
        if 'id_correlativo_flex' not in data_venta:
            data_venta['id_correlativo_flex'] = 0
        if 'envio_boleta' not in data_venta:
            data_venta['envio_boleta'] = 0

        query_venta = """
            INSERT INTO vta_ventas (total_ventas, id_apertura, envio_correo, id_cliente_fk, id_correlativo_flex, envio_boleta) 
            VALUES (%(total_ventas)s, %(id_apertura)s, %(envio_correo)s, %(id_cliente_fk)s, %(id_correlativo_flex)s, %(envio_boleta)s);
        """
        id_venta = connectToMySQL('sistemas').query_db(query_venta, data_venta)

        if not id_venta:
            return None

        # Crear los detalles de la venta
        for item in items:
            query_detalle = """
                INSERT INTO vta_detalle_ventas (id_venta, id_producto_fk, cantidad, id_listaprecio) 
                VALUES (%(id_venta)s, %(id_producto_fk)s, %(cantidad)s, %(id_listaprecio)s);
            """
            data_detalle = {
                'id_venta': id_venta,
                'id_producto_fk': item.get('id_prod'),
                'cantidad': item.get('cantidad', 0),
                # permitir que el item proporcione id_listaprecio, o usar 176 por defecto
                'id_listaprecio': item.get('id_listaprecio', 176)
            }
            connectToMySQL('sistemas').query_db(query_detalle, data_detalle)

        return id_venta
