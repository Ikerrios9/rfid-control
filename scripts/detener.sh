#!/usr/bin/env bash
# ============================================================
#   Deteniendo Sistema RFID  (Raspberry Pi / Linux)
# ============================================================
set -u

cd "$(dirname "$0")/.."

echo "============================================================"
echo "  Deteniendo Sistema RFID (Raspberry Pi)"
echo "============================================================"

# --- [1/2] Lector RFID ---------------------------------------
echo
echo "[1/2] Cerrando lector RFID (si esta corriendo)..."
if pgrep -f "lectores/lector_rfid_loop.py" >/dev/null 2>&1; then
    pkill -f "lectores/lector_rfid_loop.py" 2>/dev/null || true
    sleep 1
    # Si sigue vivo, forzar
    if pgrep -f "lectores/lector_rfid_loop.py" >/dev/null 2>&1; then
        pkill -9 -f "lectores/lector_rfid_loop.py" 2>/dev/null || true
    fi
    echo "   Lector detenido."
else
    echo "   No habia lector en ejecucion."
fi

# --- [2/2] Docker --------------------------------------------
echo
echo "[2/2] Bajando contenedores Docker (db + app)..."
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "ERROR: no se encuentra 'docker compose' ni 'docker-compose'."
    exit 1
fi

$DC down
if [ $? -ne 0 ]; then
    echo
    echo "ERROR: docker compose down fallo. Revisa que el demonio Docker este corriendo."
    exit 1
fi

echo
echo "============================================================"
echo "  Sistema RFID detenido correctamente."
echo "============================================================"
