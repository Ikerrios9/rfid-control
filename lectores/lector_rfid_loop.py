from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.Exceptions import CardRequestTimeoutException
from smartcard.CardRequest import CardRequest
from smartcard.CardType import AnyCardType
from datetime import datetime
import time
import requests

print("=== LECTOR RFID - Ejecutando en Mac ===")

# Conexión a la API del contenedor Docker
API_URL = "http://localhost:8000"

while True:
    try:
        card_request = CardRequest(timeout=5, cardType=AnyCardType())
        card_service = card_request.waitforcard()

        connection = card_service.connection
        connection.connect()

        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        data, sw1, sw2 = connection.transmit(GET_UID)

        if sw1 == 0x90 and sw2 == 0x00:
            uid_clean = toHexString(data).replace(" ", "").upper()
            print(f"\n✅ Tarjeta detectada: {uid_clean}")

            # Enviar al servidor Docker
            try:
                requests.post(f"{API_URL}/api/tarjeta", json={"uid": uid_clean}, timeout=3)
            except:
                print("   → Enviado al servidor")

        connection.disconnect()
        time.sleep(1.5)

    except CardRequestTimeoutException:
        continue
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)