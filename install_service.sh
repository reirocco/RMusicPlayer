#!/bin/bash

# --- Configurazione ---
SERVICE_NAME="rmusicplayer"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

# --- Controllo Root ---
if [ "$EUID" -ne 0 ]; then
  echo "❌ Errore: Esegui questo script con sudo."
  exit 1
fi

# --- Rilevamento Utente e Percorsi ---
ACTUAL_USER=${SUDO_USER:-$(whoami)}
WORK_DIR=$(pwd)
VENV_DIR="$WORK_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

echo "🎵 RMusicPlayer Installer v3.0"
echo "--------------------------------"
echo "Utente: $ACTUAL_USER"
echo "Cartella: $WORK_DIR"

# --- Installazione Dipendenze di Sistema (FFmpeg) ---
echo "📦 Controllo dipendenze di sistema..."

if command -v apt-get &> /dev/null; then
    echo "   Rilevato sistema Debian/Ubuntu (apt)."
    apt-get update -qq
    apt-get install -y ffmpeg python3-venv python3-dev build-essential
elif command -v pacman &> /dev/null; then
    echo "   Rilevato sistema Arch Linux (pacman)."
    pacman -Sy --noconfirm ffmpeg python
elif command -v dnf &> /dev/null; then
    echo "   Rilevato sistema Fedora/RHEL (dnf)."
    dnf install -y ffmpeg python3-devel
else
    echo "⚠️  Gestore pacchetti non riconosciuto. Assicurati di aver installato FFmpeg manualmente."
fi

# --- Setup Ambiente Python (Venv) ---
echo "🐍 Configurazione ambiente Python..."

# Cambia proprietario della cartella all'utente reale per evitare problemi di permessi
chown -R $ACTUAL_USER:$ACTUAL_USER $WORK_DIR

# Eseguiamo il setup del venv come utente normale, non root
sudo -u $ACTUAL_USER bash <<EOF
if [ ! -d "$VENV_DIR" ]; then
    echo "   Creazione virtualenv in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "   Installazione librerie Python..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$WORK_DIR/requirements.txt"
EOF

# --- Creazione Servizio Systemd ---
echo "⚙️  Creazione servizio systemd..."

cat <<EOF > $SERVICE_PATH
[Unit]
Description=RMusicPlayer Automix Server
After=network.target sound.target

[Service]
User=$ACTUAL_USER
Group=$ACTUAL_USER
WorkingDirectory=$WORK_DIR
# Importante: Usa il Python del virtualenv
ExecStart=$VENV_PYTHON $WORK_DIR/app.py
Restart=always
RestartSec=5
# Variabili d'ambiente per Pygame headless
Environment=PYTHONUNBUFFERED=1
Environment=SDL_AUDIODRIVER=alsa

[Install]
WantedBy=multi-user.target
EOF

chmod 644 $SERVICE_PATH

# --- Attivazione ---
echo "🚀 Avvio del servizio..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

# --- Verifica ---
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Installazione completata! RMusicPlayer è attivo."
    echo "   Web Interface: http://$(hostname -I | awk '{print $1}'):5000"
else
    echo "❌ Qualcosa è andato storto. Controlla i log con:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
fi