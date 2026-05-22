"""Sincroniza la base de datos local de la Raspberry Pi con la copia en Render.

Pensado para ejecutarse cada 20 minutos (cron en la Pi). Estrategia:

- `usuarios`     -> upsert por uid_limpio.
- `admin_users`  -> upsert por username.
- `accesos`      -> incremental: se copian solo los registros con id mayor
                    que el máximo id ya presente en la nube.

Variables de entorno necesarias:
- DATABASE_URL          (o DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME) -> Pi local.
- CLOUD_DATABASE_URL    -> connection string de Render (formato postgres://...).
"""
import os
import sys
import time
import psycopg2
from psycopg2.extras import execute_values

from db import DB


BATCH_SIZE = 500


def _connect_local():
    return DB().connect()


def _connect_cloud():
    dsn = os.getenv("CLOUD_DATABASE_URL")
    if not dsn:
        print("ERROR: CLOUD_DATABASE_URL no está definida", file=sys.stderr)
        sys.exit(1)
    return psycopg2.connect(dsn)


def sync_usuarios(local, cloud):
    cur_local = local.cursor()
    cur_local.execute(
        "SELECT uid_limpio, nombre, fecha_registro, notas, ultimo_evento FROM usuarios"
    )
    rows = cur_local.fetchall()
    if not rows:
        return 0

    cur_cloud = cloud.cursor()
    execute_values(
        cur_cloud,
        """
        INSERT INTO usuarios (uid_limpio, nombre, fecha_registro, notas, ultimo_evento)
        VALUES %s
        ON CONFLICT (uid_limpio) DO UPDATE SET
            nombre = EXCLUDED.nombre,
            fecha_registro = EXCLUDED.fecha_registro,
            notas = EXCLUDED.notas,
            ultimo_evento = EXCLUDED.ultimo_evento
        """,
        rows,
    )
    cloud.commit()
    return len(rows)


def sync_admins(local, cloud):
    cur_local = local.cursor()
    cur_local.execute(
        "SELECT username, password_hash, nombre_completo, rol, activo FROM admin_users"
    )
    rows = cur_local.fetchall()
    if not rows:
        return 0

    cur_cloud = cloud.cursor()
    execute_values(
        cur_cloud,
        """
        INSERT INTO admin_users (username, password_hash, nombre_completo, rol, activo)
        VALUES %s
        ON CONFLICT (username) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            nombre_completo = EXCLUDED.nombre_completo,
            rol = EXCLUDED.rol,
            activo = EXCLUDED.activo
        """,
        rows,
    )
    cloud.commit()
    return len(rows)


def sync_accesos(local, cloud):
    cur_cloud = cloud.cursor()
    cur_cloud.execute("SELECT COALESCE(MAX(id), 0) FROM accesos")
    max_remote_id = cur_cloud.fetchone()[0]

    cur_local = local.cursor()
    total = 0
    while True:
        cur_local.execute(
            """
            SELECT id, fecha_hora, uid_limpio, nombre, evento
            FROM accesos
            WHERE id > %s
            ORDER BY id ASC
            LIMIT %s
            """,
            (max_remote_id, BATCH_SIZE),
        )
        batch = cur_local.fetchall()
        if not batch:
            break

        execute_values(
            cur_cloud,
            """
            INSERT INTO accesos (id, fecha_hora, uid_limpio, nombre, evento)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            batch,
        )
        cloud.commit()

        max_remote_id = batch[-1][0]
        total += len(batch)

    # Reajustar la secuencia para que los próximos inserts en la nube
    # no choquen con ids ya sincronizados (por si la nube llega a recibir
    # escrituras propias).
    cur_cloud.execute(
        "SELECT setval('accesos_id_seq', GREATEST((SELECT COALESCE(MAX(id), 1) FROM accesos), 1))"
    )
    cloud.commit()
    return total


def main():
    start = time.time()
    print(f"[sync] arrancando ({time.strftime('%Y-%m-%d %H:%M:%S')})")

    local = _connect_local()
    cloud = _connect_cloud()
    try:
        u = sync_usuarios(local, cloud)
        a = sync_admins(local, cloud)
        ac = sync_accesos(local, cloud)
        elapsed = time.time() - start
        print(
            f"[sync] OK usuarios={u} admins={a} accesos_nuevos={ac} "
            f"en {elapsed:.1f}s"
        )
    except Exception as e:
        print(f"[sync] ERROR: {e}", file=sys.stderr)
        try:
            cloud.rollback()
        except Exception:
            pass
        sys.exit(1)
    finally:
        local.close()
        cloud.close()


if __name__ == "__main__":
    main()
