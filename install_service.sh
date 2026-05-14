#!/bin/bash

# --- Configurazione ---
SERVICE_NAME="rmusicplayer"
SERVICE_PATH="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

# --- Controllo Root ---
if [ "$EUID" -eq 0 ]; then
  echo "❌ Errore: Esegui questo script come utente normale, NON con sudo."
  exit 1
fi

# --- Rilevamento Utente e Percorsi ---
ACTUAL_USER=$(whoami)
WORK_DIR=$(pwd)
VENV_DIR="$WORK_DIR/.venv"

echo "🎵 RMusicPlayer Installer v4.0 (User Mode)"
echo "--------------------------------"
echo "Utente: $ACTUAL_USER"
echo "Cartella: $WORK_DIR"

# --- Installazione Dipendenze di Sistema ---
echo "📦 Controllo dipendenze di sistema (potrebbe essere richiesta la password per sudo)..."

if command -v apt-get &> /dev/null; then
    echo "   Rilevato sistema Debian/Ubuntu (apt)."
    sudo apt-get update -qq
    sudo apt-get install -y ffmpeg python3-venv python3-dev build-essential screen libsndfile1
elif command -v pacman &> /dev/null; then
    echo "   Rilevato sistema Arch Linux (pacman)."
    sudo pacman -Sy --noconfirm ffmpeg python screen libsndfile
elif command -v dnf &> /dev/null; then
    echo "   Rilevato sistema Fedora/RHEL (dnf)."
    sudo dnf install -y ffmpeg python3-devel screen libsndfile
else
    echo "⚠️  Gestore pacchetti non riconosciuto. Assicurati di aver installato FFmpeg, screen e libsndfile manualmente."
fi

# --- Setup Ambiente Python (Venv) ---
echo "🐍 Configurazione ambiente Python..."

if [ ! -d "$VENV_DIR" ]; then
    echo "   Creazione virtualenv in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "   Installazione librerie Python..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$WORK_DIR/requirements.txt"

# --- Creazione Script di Avvio (Wrapper) ---
START_SCRIPT="$WORK_DIR/start.sh"
echo "📄 Creazione script di avvio ($START_SCRIPT)..."

cat <<EOF > "$START_SCRIPT"
#!/bin/bash
cd "$WORK_DIR"
source "$VENV_DIR/bin/activate"
exec python3 app.py
EOF

chmod +x "$START_SCRIPT"

# --- Creazione Servizio Systemd ---
echo "⚙️  Creazione servizio systemd (Utente)..."

mkdir -p "$(dirname "$SERVICE_PATH")"

cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=RMusicPlayer Server
After=network.target sound.target

[Service]
WorkingDirectory=$WORK_DIR
ExecStart=$START_SCRIPT
Restart=always
RestartSec=5
# Variabili d'ambiente per Pygame headless
Environment=PYTHONUNBUFFERED=1
Environment=SDL_AUDIODRIVER=alsa
Environment=XDG_RUNTIME_DIR=/run/user/\$(id -u)

[Install]
WantedBy=default.target
EOF

chmod 644 "$SERVICE_PATH"

# --- Abilitazione Linger ---
echo "🕒 Abilitazione esecuzione in background senza login (linger)..."
sudo loginctl enable-linger "$ACTUAL_USER"

# --- Creazione Icona Desktop ---
echo "🖥️  Creazione icona applicazione..."
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

DESKTOP_FILE="$DESKTOP_DIR/rmusicplayer.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Name=RMusicPlayer
Comment=Avvia l'interfaccia web di RMusicPlayer
Exec=xdg-open http://localhost:5000
Icon=multimedia-audio-player
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
EOF

chmod +x "$DESKTOP_FILE"

# --- Attivazione ---
echo "🚀 Avvio del servizio..."
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"

# --- Verifica ---
if systemctl --user is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Installazione completata! RMusicPlayer è attivo come servizio utente."
    echo "   Web Interface: http://localhost:5000"
    echo "   Icona 'RMusicPlayer' aggiunta nel menu delle applicazioni!"
else
    echo "❌ Qualcosa è andato storto. Controlla i log con:"
    echo "   systemctl --user status $SERVICE_NAME"
    echo "   journalctl --user -u $SERVICE_NAME -f"
fi