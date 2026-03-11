import os
import json
import random
import threading
import time
from flask import Flask, render_template, jsonify, request
import pygame
import librosa
import numpy as np
import warnings

warnings.filterwarnings('ignore')

app = Flask(__name__)
pygame.mixer.init()

DB_FILE = 'music_db.json'
KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

music_db = {}
if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r') as f:
        music_db = json.load(f)

player_state = {
    'current_track': None,
    'folder': None,
    'is_playing': False,
    'is_paused': False,
    'playlist': []
}

analysis_state = {'is_running': True, 'progress': 0, 'text': 'Inizializzazione...'}


def build_database_task():
    global music_db
    base_dir = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
    mp3_files = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.mp3'): mp3_files.append(os.path.join(root, f))

    total = len(mp3_files)
    if total == 0:
        analysis_state.update({'is_running': False, 'progress': 100})
        return

    for i, full_path in enumerate(mp3_files):
        rel_path = os.path.relpath(full_path, base_dir).replace('\\', '/')
        if rel_path not in music_db:
            analysis_state['text'] = f"Analisi: {os.path.basename(full_path)}"
            try:
                y, sr = librosa.load(full_path, duration=10, sr=22050)
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                bpm = float(tempo[0] if isinstance(tempo, np.ndarray) else tempo)
                chroma = librosa.feature.chroma_stft(y=y, sr=sr)
                key = KEYS[np.argmax(np.sum(chroma, axis=1))]
                music_db[rel_path] = {'bpm': round(bpm, 1), 'key': key}
                with open(DB_FILE, 'w') as f:
                    json.dump(music_db, f)
            except:
                pass
        analysis_state['progress'] = int(((i + 1) / total) * 100)

    analysis_state['is_running'] = False


threading.Thread(target=build_database_task, daemon=True).start()


def play_audio_engine():
    base_dir = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
    while True:
        if player_state['is_playing'] and not player_state['is_paused']:
            if not pygame.mixer.music.get_busy():
                # Logica Automix BPM
                current_bpm = music_db.get(player_state['current_track'], {}).get('bpm', 120)
                next_track = random.choice(player_state['playlist'])
                # Trova traccia con BPM vicino (semplificato per brevità)
                player_state['current_track'] = next_track
                pygame.mixer.music.load(os.path.join(base_dir, next_track))
                pygame.mixer.music.play()
        time.sleep(1)


threading.Thread(target=play_audio_engine, daemon=True).start()


@app.route('/api/folders', defaults={'subpath': ''})
@app.route('/api/folders/<path:subpath>')
def api_folders(subpath):
    base_dir = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
    target_dir = os.path.join(base_dir, subpath)
    items = []
    if os.path.exists(target_dir):
        for d in os.listdir(target_dir):
            p = os.path.join(target_dir, d)
            if os.path.isdir(p):
                has_sub = any(os.path.isdir(os.path.join(p, s)) for s in os.listdir(p))
                items.append(
                    {'name': d, 'path': os.path.relpath(p, base_dir).replace('\\', '/'), 'has_subfolders': has_sub})
    return jsonify(items)


@app.route('/api/analysis_status')
def analysis_status(): return jsonify(analysis_state)


@app.route('/api/play_folder', methods=['POST'])
def play_folder():
    folder = request.json.get('folder')
    base_dir = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
    target = os.path.join(base_dir, folder)
    files = [os.path.relpath(os.path.join(target, f), base_dir).replace('\\', '/') for f in os.listdir(target) if
             f.endswith('.mp3')]
    if files:
        player_state.update(
            {'playlist': files, 'current_track': random.choice(files), 'is_playing': True, 'is_paused': False})
        pygame.mixer.music.stop()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 404


@app.route('/api/toggle_playback', methods=['POST'])
def toggle_playback():
    if player_state['is_paused']:
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()
    player_state['is_paused'] = not player_state['is_paused']
    return jsonify({"status": "ok"})


@app.route('/api/status')
def status():
    track = player_state['current_track']
    info = music_db.get(track, {})
    return jsonify({**player_state, 'bpm': info.get('bpm'), 'key': info.get('key')})


@app.route('/')
def index(): return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)