import os
import random
from flask import Flask, render_template, jsonify, send_from_directory

app = Flask(__name__)


# Funzione per creare la cartella RMusicPlayer nella home directory se non esiste
def ensure_music_directory_exists():
    home_directory = os.path.expanduser("~")
    music_directory = os.path.join(home_directory, 'RMusicPlayer')

    # Controlla se la cartella esiste, altrimenti la crea
    if not os.path.exists(music_directory):
        os.makedirs(music_directory)
        print(f"Cartella 'RMusicPlayer' creata in {music_directory}")
    else:
        print(f"Cartella 'RMusicPlayer' già esistente in {music_directory}")


# Chiama la funzione per assicurarsi che la cartella esista
ensure_music_directory_exists()


# Funzione per ottenere tutte le cartelle nella cartella RMusicPlayer
def get_music_directories():
    home_directory = os.path.expanduser("~")
    music_directory = os.path.join(home_directory, 'RMusicPlayer')

    if os.path.exists(music_directory) and os.path.isdir(music_directory):
        directories = [d for d in os.listdir(music_directory) if os.path.isdir(os.path.join(music_directory, d))]
        return directories
    return []


# Funzione per ottenere tutti i file mp3 di una cartella specifica
def get_mp3_files(folder_name):
    home_directory = os.path.expanduser("~")
    music_directory = os.path.join(home_directory, 'RMusicPlayer', folder_name)

    if os.path.exists(music_directory) and os.path.isdir(music_directory):
        mp3_files = [f for f in os.listdir(music_directory) if f.endswith('.mp3')]
        return mp3_files
    return []


# Route per servire i file mp3 dalla cartella RMusicPlayer
@app.route('/get_songs/<folder>')
def get_songs(folder):
    mp3_files = get_mp3_files(folder)
    random.shuffle(mp3_files)  # Ordina le canzoni in maniera casuale
    return jsonify(mp3_files)


# Route per servire i file MP3
@app.route('/serve_music/<folder>/<filename>')
def serve_music(folder, filename):
    home_directory = os.path.expanduser("~")
    music_directory = os.path.join(home_directory, 'RMusicPlayer', folder)
    return send_from_directory(music_directory, filename)


@app.route('/')
def index():
    folders = get_music_directories()
    return render_template('index.html', folders=folders)


if __name__ == '__main__':
    app.run(debug=True)
