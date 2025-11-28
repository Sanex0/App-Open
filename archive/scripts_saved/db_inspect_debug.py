import os
import sys

# Ensure project root is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask_app.config.conexiones import connectToMySQL

"""
Script de inspección rápida de la base MySQL usada por la app.
Imprime: nombre de la base conectada, existencia de tablas relevantes,
conteo de filas y algunas filas de ejemplo.

Uso:
  & C:/path/to/venv/Scripts/Activate.ps1
  python flask_app/scripts/db_inspect_debug.py

"""


def try_query(db, q, data=None):
    try:
        res = db.query_db(q, data) if data else db.query_db(q)
        return res
    except Exception as e:
        print(f"[ERROR] Query failed: {e}\n  SQL: {q}\n  Data: {data}")
        return None


def main():
    db = connectToMySQL('sistemas')

    # 1) Base actual
    print('\n[INSPECT] SELECT DATABASE()')
    cur_db = try_query(db, 'SELECT DATABASE() as db;')
    print('->', cur_db)

    # 2) Listar tablas que nos interesan
    tables = ['vta_catalogo_porcaja', 'vta_productos', 'vta_productosporcajas', 'vta_productosporcaja', 'vta_productos']
    print('\n[INSPECT] Buscando tablas relevantes')
    for t in tables:
        q = f"SHOW TABLES LIKE '{t}';"
        r = try_query(db, q)
        print(f"TABLE {t}:", r)

    # 3) Conteos y muestras
    targets = ['vta_catalogo_porcaja', 'vta_productos']
    for t in targets:
        print(f"\n[INSPECT] Conteo y muestra para {t}")
        q_count = f"SELECT COUNT(*) as cnt FROM {t};"
        cnt = try_query(db, q_count)
        print('COUNT ->', cnt)

        q_sample = f"SELECT * FROM {t} LIMIT 20;"
        sample = try_query(db, q_sample)
        print('SAMPLE ->')
        print(sample)

    # 4) Ejecutar la misma join que probaste
    q_join = """
        SELECT a.id_caja, b.id_prod, c.descripcion_prod
        FROM vta_cajas a
        JOIN vta_catalogo_porcaja b ON a.id_caja = b.id_caja
        JOIN vta_productos c ON b.id_prod = c.id_prod
        WHERE a.id_caja = %(id_caja)s;
    """
    print('\n[INSPECT] Ejecutando join exacta (id_caja=9)')
    rjoin = try_query(db, q_join, {'id_caja': 9})
    print('JOIN ->', rjoin)

    print('\n[INSPECT] Fin.')


if __name__ == '__main__':
    main()
