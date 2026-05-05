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

echo "🎵 RMusicPlayer Installer v3.0"
echo "--------------------------------"
echo "Utente: $ACTUAL_USER"
echo "Cartella: $WORK_DIR"

# --- Installazione Dipendenze di Sistema ---
echo "📦 Controllo dipendenze di sistema..."

if command -v apt-get &> /dev/null; then
    echo "   Rilevato sistema Debian/Ubuntu (apt)."
    apt-get update -qq
    apt-get install -y ffmpeg python3-venv python3-dev build-essential screen libsndfile1
elif command -v pacman &> /dev/null; then
    echo "   Rilevato sistema Arch Linux (pacman)."
    pacman -Sy --noconfirm ffmpeg python screen libsndfile
elif command -v dnf &> /dev/null; then
    echo "   Rilevato sistema Fedora/RHEL (dnf)."
    dnf install -y ffmpeg python3-devel screen libsndfile
else
    echo "⚠️  Gestore pacchetti non riconosciuto. Assicurati di aver installato FFmpeg, screen e libsndfile manualmente."
fi

# --- Setup Ambiente Python (Venv) ---
echo "🐍 Configurazione ambiente Python..."

# Cambia proprietario della cartella all'utente reale per evitare problemi di permessi
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$WORK_DIR"

# Eseguiamo il setup del venv come utente normale
sudo -u "$ACTUAL_USER" bash <<EOF
if [ ! -d "$VENV_DIR" ]; then
    echo "   Creazione virtualenv in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "   Installazione librerie Python..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$WORK_DIR/requirements.txt"
EOF

# --- Creazione Script di Avvio (Wrapper) ---
# Questo garantisce che il venv venga effettivamente attivato prima di lanciare l'app
START_SCRIPT="$WORK_DIR/start.sh"
echo "📄 Creazione script di avvio ($START_SCRIPT)..."

cat <<EOF > "$START_SCRIPT"
#!/bin/bash
cd "$WORK_DIR"
source "$VENV_DIR/bin/activate"
exec python3 app.py
EOF

chown "$ACTUAL_USER:$ACTUAL_USER" "$START_SCRIPT"
chmod +x "$START_SCRIPT"

# --- Creazione Servizio Systemd ---
echo "⚙️  Creazione servizio systemd..."

cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=RMusicPlayer Server
After=network.target sound.target

[Service]
User=$ACTUAL_USER
Group=$ACTUAL_USER
WorkingDirectory=$WORK_DIR
# Usiamo lo script di avvio appena creato che attiva il venv
ExecStart=$START_SCRIPT
Restart=always
RestartSec=5
# Variabili d'ambiente per Pygame headless
Environment=PYTHONUNBUFFERED=1
Environment=SDL_AUDIODRIVER=alsa

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_PATH"

# --- Creazione Icona Desktop ---
echo "🖥️  Creazione icona applicazione..."
DESKTOP_DIR="/home/$ACTUAL_USER/.local/share/applications"
sudo -u "$ACTUAL_USER" mkdir -p "$DESKTOP_DIR"

DESKTOP_FILE="$DESKTOP_DIR/rmusicplayer.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Name=RMusicPlayer
Comment=Avvia l'interfaccia web di RMusicPlayer
# L'icona apre direttamente il browser verso il server locale
Exec=xdg-open http://localhost:5000
Icon=multimedia-audio-player
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
EOF

chown "$ACTUAL_USER:$ACTUAL_USER" "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

# --- Attivazione ---
echo "🚀 Avvio del servizio..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# --- Verifica ---
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Installazione completata! RMusicPlayer è attivo."
    echo "   Web Interface: http://localhost:5000"
    echo "   Icona 'RMusicPlayer' aggiunta nel menu delle applicazioni!"
else
    echo "❌ Qualcosa è andato storto. Controlla i log con:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
fi