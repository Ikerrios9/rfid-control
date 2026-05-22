#!/usr/bin/env bash
# ============================================================
#   Instala accesos directos en el escritorio de la Raspberry Pi
#   para iniciar.sh y detener.sh (doble clic = ejecutar).
# ============================================================
set -eu

# Ruta absoluta a la carpeta del proyecto (un nivel por encima de scripts/)
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Asegurar permisos de ejecucion en los .sh
chmod +x "$SCRIPTS_DIR/iniciar.sh" "$SCRIPTS_DIR/detener.sh" "$0"

# Detectar carpeta de escritorio del usuario
if command -v xdg-user-dir >/dev/null 2>&1; then
    DESKTOP_DIR="$(xdg-user-dir DESKTOP)"
else
    DESKTOP_DIR="$HOME/Desktop"
fi
mkdir -p "$DESKTOP_DIR"

echo "Proyecto: $PROJECT_DIR"
echo "Escritorio: $DESKTOP_DIR"

# --- Lanzador: Iniciar RFID ----------------------------------
cat > "$DESKTOP_DIR/Iniciar-RFID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Iniciar RFID
Comment=Arranca el sistema RFID (docker + lector)
Exec=lxterminal --title="Iniciar RFID" -e bash -c "$SCRIPTS_DIR/iniciar.sh; echo; echo 'Pulsa ENTER para cerrar...'; read"
Icon=utilities-terminal
Terminal=false
Categories=Utility;
EOF

# --- Lanzador: Detener RFID ----------------------------------
cat > "$DESKTOP_DIR/Detener-RFID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Detener RFID
Comment=Detiene el sistema RFID (docker + lector)
Exec=lxterminal --title="Detener RFID" -e bash -c "$SCRIPTS_DIR/detener.sh; echo; echo 'Pulsa ENTER para cerrar...'; read"
Icon=process-stop
Terminal=false
Categories=Utility;
EOF

# Marcar como ejecutables (PIXEL/LXDE pide esto para no avisar)
chmod +x "$DESKTOP_DIR/Iniciar-RFID.desktop" "$DESKTOP_DIR/Detener-RFID.desktop"

# En Raspberry Pi OS reciente, marcar como "confiables" para que no pregunte
if command -v gio >/dev/null 2>&1; then
    gio set "$DESKTOP_DIR/Iniciar-RFID.desktop" metadata::trusted true 2>/dev/null || true
    gio set "$DESKTOP_DIR/Detener-RFID.desktop" metadata::trusted true 2>/dev/null || true
fi

echo
echo "Listo. Accesos directos creados en el escritorio:"
echo "  - Iniciar RFID"
echo "  - Detener RFID"
echo
echo "Si al hacer doble clic pide confirmacion, marca 'Confiar y ejecutar' una vez."
