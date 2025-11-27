import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from flask_app.config.conexiones import connectToMySQL, connectToSQLServer

# Prueba MySQL
try:
    mysql = connectToMySQL('sistemas')
    result = mysql.query_db('SELECT 1 AS test')
    print('MySQL OK:', result)
except Exception as e:
    print('Error MySQL:', e)

# Prueba SQL Server
try:
    sql = connectToSQLServer(user='flexline', password='flexline')
    result = sql.query_db('SELECT 1 AS test')
    print('SQL Server OK:', result)
except Exception as e:
    print('Error SQL Server:', e)
