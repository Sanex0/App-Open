from flask_app.config.conexiones import connectToMySQL, connectToSQLServer

class Producto:
    def __init__(self, data):
        self.id_prod = data.get('id_prod')
        self.id_producto = data.get('id_producto')
        self.nombre = data.get('nombre')
        self.precio = data.get('precio')
        self.compuesto = data.get('compuesto')
        self.kitvirtual = data.get('kitvirtual')

    @classmethod
    def get_by_caja(cls, id_caja):
        # 1. Obtener IDs de producto desde MySQL
        mysql_query = """
            SELECT p.id_prod, p.descripcion_prod
            FROM vta_productos p
            JOIN vta_catalogo_porcaja cat ON p.id_prod = cat.id_prod
            WHERE cat.id_caja = %(id_caja)s;
        """
        data = {'id_caja': id_caja}
        mysql_results = connectToMySQL('sistemas').query_db(mysql_query, data)

        if not mysql_results:
            return []

        # Extraer los códigos de producto (campo `descripcion_prod`) para la consulta a SQL Server
        # Filtrar/limpiar valores nulos
        product_ids = [row['descripcion_prod'] for row in mysql_results if row.get('descripcion_prod')]
        
        # 2. Obtener detalles de productos desde SQL Server
        # El placeholder "?" es para pyodbc, que es común en conexiones a SQL Server
        placeholders = ','.join(['?'] * len(product_ids))
        
        sql_server_query = f"""
            SELECT 
                p.PRODUCTO as id_producto, 
                p.GLOSA as nombre, 
                l.Valor * 1.19 AS precio,
                p.COMPUESTO as compuesto,
                p.KitVirtual as kitvirtual
            FROM flexline.ListaPrecioD l
            JOIN flexline.producto p ON l.Empresa = p.EMPRESA AND l.Producto = p.PRODUCTO
            WHERE l.IdLisPrecio = 176 AND p.PRODUCTO IN ({placeholders})
            ORDER BY p.GLOSA;
        """
        
        # La función de conexión debería poder manejar los parámetros de forma segura
        try:
            sql_server_results = connectToSQLServer('BDFlexline').query_db(sql_server_query, tuple(product_ids))
        except Exception as e:
            print(f"Error connecting to SQL Server: {e}")
            return [] # Retornar vacío si falla la conexión

        # 3. Mapear detalles a los productos
        productos_dict = {row['id_producto']: row for row in sql_server_results}
        
        final_products = []
        for row in mysql_results:
            codigo = row.get('descripcion_prod')
            product_detail = productos_dict.get(codigo)
            if product_detail:
                # Combinar la información
                full_product_data = {
                    'id_prod': row.get('id_prod'),
                    'id_producto': codigo,
                    **product_detail
                }
                final_products.append(cls(full_product_data))
        
        return final_products
