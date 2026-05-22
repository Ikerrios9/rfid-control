#!/usr/bin/env bash
# ============================================================
#   Iniciando Sistema RFID  (Raspberry Pi / Linux)
# ============================================================
set -u

cd "$(dirname "$0")/.."

echo "============================================================"
echo "  Iniciando Sistema RFID (Raspberry Pi)"
echo "============================================================"

# --- [0/5] Servicio pcscd (lector USB) ------------------------
echo
echo "[0/5] Verificando servicio pcscd (lector RFID USB)..."
if command -v systemctl >/dev/null 2>&1; then
    if ! systemctl is-active --quiet pcscd; then
        echo "   pcscd no esta activo. Intentando arrancarlo..."
        sudo systemctl start pcscd || {
            echo "   ADVERTENCIA: no se pudo arrancar pcscd. El lector puede no funcionar."
        }
    else
        echo "   pcscd ya esta activo."
    fi
else
    echo "   systemctl no disponible, se omite la verificacion de pcscd."
fi

# --- [1/5] Docker --------------------------------------------
echo
echo "[1/5] Levantando Docker (db + app)..."
if command -v docker >/dev/null 2>&1; then
    if docker compose version >/dev/null 2>&1; then
        DC="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        DC="docker-compose"
    else
        echo "ERROR: no se encuentra 'docker compose' ni 'docker-compose'."
        exit 1
    fi
else
    echo "ERROR: docker no esta instalado. Instala docker.io y docker compose."
    exit 1
fi

$DC up -d
if [ $? -ne 0 ]; then
    echo
    echo "ERROR: docker compose fallo. Revisa que el demonio Docker este corriendo."
    exit 1
fi

# --- [2/5] Esperar API ---------------------------------------
echo
echo "[2/5] Esperando a que la API responda en http://localhost:8000 ..."
tries=0
status=""
while :; do
    tries=$((tries + 1))
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/login 2>/dev/null || echo "000")
    case "$status" in
        200|301|302|303|401) break ;;
    esac
    if [ "$tries" -ge 30 ]; then
        echo "   ADVERTENCIA: La API no respondio tras 30 intentos. Continuando igualmente."
        break
    fi
    sleep 1
done
echo "   API lista (HTTP $status)."

# --- [3/5] Abrir navegador (solo si hay sesion grafica) ------
echo
echo "[3/5] Abriendo navegador..."
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    # Panel principal
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:8000/" >/dev/null 2>&1 &
    elif command -v chromium-browser >/dev/null 2>&1; then
        chromium-browser "http://localhost:8000/" >/dev/null 2>&1 &
    fi
    # Pantalla /display en ventana nueva
    if command -v chromium-browser >/dev/null 2>&1; then
        chromium-browser --new-window "http://localhost:8000/display" >/dev/null 2>&1 &
    elif command -v chromium >/dev/null 2>&1; then
        chromium --new-window "http://localhost:8000/display" >/dev/null 2>&1 &
    elif command -v firefox >/dev/null 2>&1; then
        firefox --new-window "http://localhost:8000/display" >/dev/null 2>&1 &
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:8000/display" >/dev/null 2>&1 &
    fi
else
    echo "   Sin sesion grafica (DISPLAY vacio). Acceso desde otro equipo:"
    IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    echo "      http://${IP:-<ip-de-la-pi>}:8000/"
    echo "      http://${IP:-<ip-de-la-pi>}:8000/display"
fi

# --- [4/5] Lector RFID ---------------------------------------
echo
echo "[4/5] Iniciando lector RFID en la Raspberry Pi..."
echo "============================================================"
# Detener cualquier instancia previa del lector
pkill -f "lectores/lector_rfid_loop.py" 2>/dev/null || true
exec python3 lectores/lector_rfid_loop.py
