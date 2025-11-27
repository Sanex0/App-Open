import pymysql.cursors
import pyodbc

class MySQLConnection:
    def __init__(self, db='sistemas'):
        print(f"[MySQLConnection] Conectando a la base de datos: {db}")
        connection = pymysql.connect(
            host='181.212.204.13',
            port=3306,
            user='root',
            password='1Qazxsw2123_?',
            db=db,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        connection.autocommit(True)
        self.connection = connection
        print("[MySQLConnection] Conexión establecida.")

    def query_db(self, query, data=None):
        print(f"[MySQLConnection] Ejecutando query: {query} | Data: {data}")
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, data) if data else cursor.execute(query)
                if query.strip().lower().startswith("insert"):
                    self.connection.commit()
                    print("[MySQLConnection] Insert realizado, lastrowid:", cursor.lastrowid)
                    return cursor.lastrowid
                elif query.strip().lower().startswith("select"):
                    result = cursor.fetchall()
                    print(f"[MySQLConnection] Select retornó {len(result)} filas.")
                    return result
                else:
                    self.connection.commit()
                    print("[MySQLConnection] Query ejecutada y commit realizado.")
                    return True
        except Exception as e:
            print("[MySQLConnection] Error:", e)
            if query.strip().lower().startswith("select"):
                return []
            return False

def connectToMySQL(db):
    return MySQLConnection(db)

class SQLServerConnection:
    def __init__(self, db='BDFlexline', user='flexline', password='flexline'):
        # Usa un driver más universal y moderno para Linux y Windows
        connection_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=192.168.1.150,1433;"
            f"DATABASE={db};"
            f"UID={user};"
            f"PWD={password};"
        )
        self.connection = pyodbc.connect(connection_str)

    def query_db(self, query, data=None):
        cursor = self.connection.cursor()
        try:
            if data:
                cursor.execute(query, data)
            else:
                cursor.execute(query)
            if query.strip().lower().startswith("select"):
                return [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
            elif query.strip().lower().startswith("insert"):
                self.connection.commit()
                return cursor.lastrowid
            else:
                self.connection.commit()
        except Exception as e:
            print("SQL Server error:", e)
            return []
        finally:
            cursor.close()
            self.connection.close()

def connectToSQLServer(db='BDFlexline', user='flexline', password='flexline'):
    return SQLServerConnection(db, user, password)
