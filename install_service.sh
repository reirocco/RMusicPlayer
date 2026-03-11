#!/bin/bash

# Controllo che lo script sia eseguito con i permessi di amministratore
if [ "$EUID" -ne 0 ]; then
  echo "Errore: Per favore, esegui questo script con sudo."
  echo "Usa il comando: sudo bash install_service.sh"
  exit
fi

# Trova l'utente reale (anche se si usa sudo) e la cartella corrente
ACTUAL_USER=${SUDO_USER:-$(whoami)}
WORK_DIR=$(pwd)
SERVICE_PATH="/etc/systemd/system/rmusicplayer.service"

echo "Inizio l'installazione del servizio RMusicPlayer..."
echo "Utente rilevato: $ACTUAL_USER"
echo "Cartella rilevata: $WORK_DIR"

# Creazione del file di servizio
cat <<EOF > $SERVICE_PATH
[Unit]
Description=RMusicPlayer Automix Server
After=network.target sound.target

[Service]
User=$ACTUAL_USER
WorkingDirectory=$WORK_DIR
ExecStart=/usr/bin/python3 $WORK_DIR/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "File di servizio creato in $SERVICE_PATH"

# Ricarica systemd, abilita e avvia il servizio
echo "Ricarico i demoni di sistema..."
systemctl daemon-reload

echo "Abilito l'avvio automatico al boot..."
systemctl enable rmusicplayer.service

echo "Avvio il servizio..."
systemctl restart rmusicplayer.service

echo "Installazione completata con successo!"
echo "Ecco lo stato attuale del servizio:"
echo "---------------------------------------------------"
systemctl status rmusicplayer.service --no-pager