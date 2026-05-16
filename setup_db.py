"""Script para crear el esquema completo si no existe (PostgreSQL).

Ejecuta el contenido de database.sql contra la base de datos configurada
en DATABASE_URL o en las variables DB_HOST/DB_USER/DB_PASSWORD/DB_NAME.
"""
import os
from db import DB

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "database.sql")


def main():
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    db = DB()
    conn = db.connect()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("OK Esquema creado/verificado correctamente")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
