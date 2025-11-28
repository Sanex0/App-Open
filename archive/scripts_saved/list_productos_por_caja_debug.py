import os
import sys

# Si ejecutas el script directamente (`python flask_app/scripts/....py`) desde
# un directorio distinto al raíz del proyecto, Python puede no encontrar el
# paquete `flask_app`. Aseguramos que la raíz del proyecto esté en `sys.path`.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask_app.config.conexiones import connectToMySQL

"""
Script de depuración para listar las filas relacionadas con una `id_caja`.
Ejecuta consultas directas en MySQL para verificar si hay datos en
`vta_catalogo_porcaja` y `vta_productos`.

Uso:
  & C:/path/to/venv/Scripts/Activate.ps1
  python flask_app/scripts/list_productos_por_caja_debug.py 9

"""


def main(id_caja):
    db = connectToMySQL('sistemas')

    q_catalogo = "SELECT * FROM vta_catalogo_porcaja WHERE id_caja = %(id_caja)s;"
    print(f"\n[DEBUG] Ejecutando: {q_catalogo} | Data: {{'id_caja': {id_caja}}}\n")
    catalogo = db.query_db(q_catalogo, {'id_caja': id_caja})
    print(f"[DEBUG] filas en vta_catalogo_porcaja: {len(catalogo) if isinstance(catalogo, list) else catalogo}")
    if isinstance(catalogo, list):
        for r in catalogo:
            print(r)

    q_productos = "SELECT * FROM vta_productos WHERE id_prod IN (SELECT id_prod FROM vta_catalogo_porcaja WHERE id_caja = %(id_caja)s);"
    print(f"\n[DEBUG] Ejecutando: {q_productos} | Data: {{'id_caja': {id_caja}}}\n")
    productos = db.query_db(q_productos, {'id_caja': id_caja})
    print(f"[DEBUG] filas en vta_productos (por id_prod): {len(productos) if isinstance(productos, list) else productos}")
    if isinstance(productos, list):
        for r in productos:
            print(r)

    q_join = """
        SELECT cat.id_prod, p.descripcion_prod
        FROM vta_catalogo_porcaja cat
        JOIN vta_productos p ON cat.id_prod = p.id_prod
        WHERE cat.id_caja = %(id_caja)s;
    """
    print(f"\n[DEBUG] Ejecutando join: {q_join.strip()} | Data: {{'id_caja': {id_caja}}}\n")
    join_rows = db.query_db(q_join, {'id_caja': id_caja})
    print(f"[DEBUG] filas en join: {len(join_rows) if isinstance(join_rows, list) else join_rows}")
    if isinstance(join_rows, list):
        for r in join_rows:
            print(r)

    print('\n[DEBUG] Fin del reporte.\n')


if __name__ == '__main__':
    id_caja = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    main(id_caja)
