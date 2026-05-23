#!/bin/bash
echo "Iniciando Sistema RFID..."

# Iniciar lector en segundo plano
python lectores/lector_rfid_loop.py > /var/log/rfid-reader.log 2>&1 &

# Sincronización a la nube cada 2 min (solo si está configurada)
if [ -n "$CLOUD_DATABASE_URL" ]; then
    echo "[sync] background sync habilitado (cada 2 min)"
    (
        while true; do
            python cloud/sync_to_cloud.py
            sleep 120
        done
    ) > /var/log/rfid-sync.log 2>&1 &
else
    echo "[sync] CLOUD_DATABASE_URL no definida, sync deshabilitado"
fi

# Iniciar API
exec python api.py