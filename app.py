import os
import random
from flask import Flask, render_template, jsonify, send_from_directory
import webbrowser

app = Flask(__name__)


def ensure_music_directory_exists():
    home_directory = os.path.expanduser("~")
    music_directory = os.path.join(home_directory, 'RMusicPlayer')
    if not os.path.exists(music_directory):
        os.makedirs(music_directory)
        print(f"Cartella 'RMusicPlayer' creata in {music_directory}")
    else:
        print(f"Cartella 'RMusicPlayer' già esistente in {music_directory}")


ensure_music_directory_exists()


# NUOVA FUNZIONE: Restituisce il contenuto di una cartella e verifica se ha sottocartelle
def get_directory_info(subpath=""):
    home_directory = os.path.expanduser("~")
    base_dir = os.path.join(home_directory, 'RMusicPlayer')
    target_dir = os.path.abspath(os.path.join(base_dir, subpath))

    # Controllo di sicurezza per impedire l'uscita dalla cartella principale
    if not target_dir.startswith(base_dir):
        return []

    if os.path.exists(target_dir) and os.path.isdir(target_dir):
        items = []
        for d in os.listdir(target_dir):
            item_path = os.path.join(target_dir, d)
            if os.path.isdir(item_path):
                # Controlla se la cartella corrente contiene a sua volta sottocartelle
                subdirs = [s for s in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, s))]
                has_subfolders = len(subdirs) > 0

                # Crea il percorso relativo per il frontend
                rel_path = os.path.relpath(item_path, base_dir).replace('\\', '/')

                items.append({
                    'name': d,
                    'path': rel_path,
                    'has_subfolders': has_subfolders
                })
        return items
    return []


# NUOVA ROTTA: API per ottenere le cartelle tramite Javascript
@app.route('/api/folders')
@app.route('/api/folders/<path:subpath>')
def api_folders(subpath=""):
    return jsonify(get_directory_info(subpath))


# MODIFICATA: Ora supporta i percorsi dinamici (sottocartelle)
@app.route('/get_songs/<path:folder_path>')
def get_songs(folder_path):
    home_directory = os.path.expanduser("~")
    base_dir = os.path.join(home_directory, 'RMusicPlayer')
    target_dir = os.path.abspath(os.path.join(base_dir, folder_path))

    if not target_dir.startswith(base_dir):
        return jsonify([])

    if os.path.exists(target_dir) and os.path.isdir(target_dir):
        mp3_files = [f for f in os.listdir(target_dir) if f.endswith('.mp3')]
        random.shuffle(mp3_files)
        return jsonify(mp3_files)
    return jsonify([])


# MODIFICATA: Gestisce la riproduzione in sicurezza anche nelle sottocartelle
@app.route('/serve_music/<path:filepath>')
def serve_music(filepath):
    home_directory = os.path.expanduser("~")
    base_dir = os.path.join(home_directory, 'RMusicPlayer')
    full_path = os.path.abspath(os.path.join(base_dir, filepath))

    if not full_path.startswith(base_dir):
        return "Access denied", 403

    folder_path = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(folder_path, filename)


@app.route('/karaoke')
def karaoke():
    return render_template('karaoke.html')


current_video_id = None


@app.route('/projector')
def projector():
    return render_template('projector_dynamic.html')


@app.route('/set_video/<video_id>')
def set_video(video_id):
    global current_video_id
    current_video_id = video_id
    return {'status': 'ok'}


@app.route('/get_video')
def get_video():
    return {'video_id': current_video_id}


# MODIFICATA: L'indice renderizza solo l'HTML, le cartelle le popola JS
@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)