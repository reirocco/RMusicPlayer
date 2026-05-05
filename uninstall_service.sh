#!/bin/bash

# --- Configurazione ---
SERVICE_NAME="rmusicplayer"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

# --- Controllo Root ---
if [ "$EUID" -ne 0 ]; then
  echo "❌ Errore: Esegui questo script con sudo."
  exit 1
fi

ACTUAL_USER=${SUDO_USER:-$(whoami)}
DESKTOP_FILE="/home/$ACTUAL_USER/.local/share/applications/rmusicplayer.desktop"

echo "🗑️  Disinstallazione RMusicPlayer Server..."
echo "--------------------------------"

# --- Fermare e disabilitare il servizio ---
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "🛑 Fermo il servizio $SERVICE_NAME..."
    systemctl stop "$SERVICE_NAME"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "🚫 Disabilito l'avvio automatico..."
    systemctl disable "$SERVICE_NAME"
fi

# --- Rimozione file di servizio systemd ---
if [ -f "$SERVICE_PATH" ]; then
    echo "🗑️  Rimuovo il file di sistema systemd..."
    rm -f "$SERVICE_PATH"
    systemctl daemon-reload
fi

# --- Rimozione icona Desktop ---
if [ -f "$DESKTOP_FILE" ]; then
    echo "🖥️  Rimuovo l'icona dell'applicazione..."
    rm -f "$DESKTOP_FILE"
fi

echo "✅ Disinstallazione completata con successo!"
echo "⚠️  Nota: La cartella del progetto e l'ambiente virtuale (.venv) NON sono stati eliminati."
echo "   Se vuoi rimuoverli completamente, puoi cancellare la cartella manualmente."
