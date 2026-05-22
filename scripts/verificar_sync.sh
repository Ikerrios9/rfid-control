#!/usr/bin/env bash
# Comprueba que la BD local de la Pi y la de Render coinciden.
# Lanza una sync forzada y compara totales + últimos accesos.

set -u

echo "============================================================"
echo "  Verificación de sincronización Pi -> Render"
echo "============================================================"

echo
echo "[1/5] Últimos 5 accesos en LOCAL (Pi)"
docker exec rfid-postgres psql -U rfid -d rfid -c \
"SELECT id, fecha_hora, uid_limpio, nombre, evento FROM accesos ORDER BY id DESC LIMIT 5;"

echo
echo "[2/5] Totales LOCAL"
docker exec rfid-postgres psql -U rfid -d rfid -t -c \
"SELECT 'usuarios='||COUNT(*) FROM usuarios
 UNION ALL SELECT 'admins='||COUNT(*) FROM admin_users
 UNION ALL SELECT 'accesos='||COUNT(*) FROM accesos;"

echo
echo "[3/5] Forzando sync a Render..."
docker exec rfid-app python cloud/sync_to_cloud.py

echo
echo "[4/5] Últimos 5 accesos en NUBE (Render)"
docker exec rfid-app python -c "
import os, psycopg2
c = psycopg2.connect(os.getenv('CLOUD_DATABASE_URL'))
cur = c.cursor()
cur.execute('SELECT id, fecha_hora, uid_limpio, nombre, evento FROM accesos ORDER BY id DESC LIMIT 5')
for r in cur.fetchall(): print(r)
"

echo
echo "[5/5] Totales NUBE"
docker exec rfid-app python -c "
import os, psycopg2
c = psycopg2.connect(os.getenv('CLOUD_DATABASE_URL'))
cur = c.cursor()
cur.execute('SELECT COUNT(*) FROM usuarios'); print('usuarios=', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM admin_users'); print('admins=', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM accesos');  print('accesos=',  cur.fetchone()[0])
"

echo
echo "============================================================"
echo "  Listo. Compara los totales LOCAL (paso 2) con NUBE (paso 5)."
echo "============================================================"
