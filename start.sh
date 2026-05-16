#!/bin/bash
echo "🚀 Iniciando Sistema RFID..."

# Iniciar lector en segundo plano
python lector_rfid_loop.py > /var/log/rfid-reader.log 2>&1 &

# Iniciar API
exec python api.py