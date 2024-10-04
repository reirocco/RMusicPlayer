#!/bin/bash

# Nome del virtual environment (modifica a piacere)
venv_name=enviroment
#pwd
# Controlla se il virtual environment esiste già
#if [ ! -d "$venv_name" ]; then
#  # Crea il virtual environment
#  python3 -m venv $venv_name
#  echo "Virtual environment creato: $venv_name"
#fi

# Attiva il virtual environment
source /opt/RMusicPlayer/$venv_name/bin/activate

# Controlla se esiste il file requirements.txt
#if [ -f requirements.txt ]; then
  # Installa i pacchetti dal file requirements.txt
#  pip install -r requirements.txt
#  echo "Pacchetti installati da requirements.txt"
#else
#  echo "File requirements.txt non trovato."
#fi

# Crea una nuova sessione screen e avvia Flask al suo interno
screen -S RMusicPlayer -dm bash -c 'flask run'
sleep 5
open http://127.0.0.1:5000 &

