import os
import json
import random
import threading
import time
import subprocess
import sys
import multiprocessing
import uuid
import datetime
import glob
from collections import deque
from flask import Flask, render_template, jsonify, request, send_file, abort
import pygame
import warnings

warnings.filterwarnings('ignore')

class LogCapture:
    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.buffer = deque(maxlen=500) 

    def write(self, message):
        try:
            self.original_stream.write(message)
            self.original_stream.flush()
            if message.strip(): 
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                self.buffer.append(f"[{timestamp}] {message.strip()}")
        except Exception: pass

    def flush(self):
        try: self.original_stream.flush()
        except: pass

    def get_logs(self): return list(self.buffer)
    
    def __getattr__(self, name): return getattr(self.original_stream, name)

if not isinstance(sys.stdout, LogCapture):
    sys.stdout = LogCapture(sys.stdout)

app = Flask(__name__)

pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(8)

CHANNEL_END_EVENTS = {0: pygame.USEREVENT + 0, 1: pygame.USEREVENT + 1}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_ROOT_DIR = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
DB_FILE = os.path.join(BASE_DIR, 'music_db.json')
STATUS_FILE = os.path.join(BASE_DIR, 'analysis_status.json')
ANALYZER_SCRIPT = os.path.join(BASE_DIR, 'analyzer.py')

if not os.path.exists(MUSIC_ROOT_DIR): os.makedirs(MUSIC_ROOT_DIR, exist_ok=True)

music_db = {}

player_state = {
    'current_track': None, 'next_track_queued': None, 'next_wav_path': None,
    'folder': None, 'is_playing': False, 'is_paused': False, 
    'playlist': [], 'queue': [], 'active_channel_id': 0, 'last_crossfade_time': 0
}

audio_lock = threading.Lock()

def validate_path(base_dir, relative_path):
    if not relative_path: return base_dir
    safe_base = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(base_dir, relative_path))
    if not target_path.startswith(safe_base): raise PermissionError("Accesso negato")
    return target_path

def clean_startup_temps():
    temps = glob.glob(os.path.join(BASE_DIR, "temp_*.wav")) + glob.glob(os.path.join(BASE_DIR, "temp_*.tmp"))
    for f in temps:
        try: os.remove(f)
        except: pass

clean_startup_temps()

def load_db():
    global music_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: music_db = json.load(f)
        except json.JSONDecodeError: pass

load_db()

def start_analyzer_process():
    if os.path.exists(ANALYZER_SCRIPT): subprocess.Popen([sys.executable, ANALYZER_SCRIPT])

start_analyzer_process()

def db_reloader():
    while True:
        load_db()
        time.sleep(5)

threading.Thread(target=db_reloader, daemon=True).start()

def are_keys_compatible(key1_camelot, key2_camelot):
    if not key1_camelot or not key2_camelot or "N/A" in [key1_camelot, key2_camelot]: return False
    num1, letter1 = int(key1_camelot[:-1]), key1_camelot[-1]
    num2, letter2 = int(key2_camelot[:-1]), key2_camelot[-1]
    if num1 == num2: return True
    if letter1 == letter2 and (num2 == num1 + 1 or (num1 == 12 and num2 == 1)): return True
    if letter1 == letter2 and (num2 == num1 - 1 or (num1 == 1 and num2 == 12)): return True
    return False

def pop_next_track():
    global player_state
    
    if not player_state['queue']:
        if not player_state['playlist']: return None
        print("[Automix] Coda vuota. Ricarico e mescolo la playlist originale.")
        player_state['queue'] = list(player_state['playlist'])

    current_track_path = player_state['current_track']
    queue = player_state['queue']

    if not current_track_path:
        chosen = random.choice(queue)
        queue.remove(chosen)
        return chosen

    current_track_data = music_db.get(current_track_path)
    if not current_track_data:
        chosen = random.choice(queue)
        queue.remove(chosen)
        return chosen
    
    candidates = [p for p in queue if p != current_track_path]
    if not candidates:
        if queue and queue[0] == current_track_path:
             queue.remove(current_track_path)
             return current_track_path
        return None

    # --- AUTOMIX 2.0: ENERGY & KEY & BPM ---
    current_bpm = current_track_data.get('bpm', 120)
    current_energy = current_track_data.get('energy', 5)
    
    # 1. Filtra per Armonia (Camelot)
    harmonic_matches = [
        p for p in candidates 
        if are_keys_compatible(current_track_data.get('camelot'), music_db.get(p, {}).get('camelot'))
    ]
    pool = harmonic_matches if harmonic_matches else candidates

    # 2. Filtra per Energia (Flow: +/- 2 livelli)
    # Se abbiamo abbastanza scelta, restringiamo il campo per mantenere l'energia
    energy_matches = [
        p for p in pool
        if abs(music_db.get(p, {}).get('energy', 5) - current_energy) <= 2
    ]
    if energy_matches: pool = energy_matches

    # 3. Ordina per BPM (più vicino vince)
    pool.sort(key=lambda p: abs(music_db.get(p, {}).get('bpm', 120) - current_bpm))
    
    chosen = pool[0]
    if chosen in queue: queue.remove(chosen)
        
    print(f"[Automix] Scelta '{chosen}' (E:{music_db.get(chosen,{}).get('energy')} BPM:{music_db.get(chosen,{}).get('bpm')})")
    return chosen

def preload_worker(mp3_path, wav_output_path, gain_db=0.0, cue_point_sec=0.0):
    try:
        if sys.platform != "win32": os.nice(19)
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(mp3_path)
        if cue_point_sec > 0:
            start_ms = int(cue_point_sec * 1000)
            if start_ms < len(audio): audio = audio[start_ms:]
        if gain_db != 0.0: audio = audio.apply_gain(gain_db)
        
        tmp_path = wav_output_path + ".tmp"
        audio.export(tmp_path, format="wav")
        os.rename(tmp_path, wav_output_path)
    except Exception as e:
        print(f"[Worker] Errore: {e}")

def schedule_preload():
    with audio_lock:
        if not player_state['playlist'] and not player_state['queue']: return
        if player_state['next_track_queued'] and player_state['next_wav_path']: return

        next_track_path = pop_next_track()
        if not next_track_path: return 

        unique_wav = os.path.join(BASE_DIR, f"temp_{uuid.uuid4().hex}.wav")
        player_state['next_track_queued'] = next_track_path
        player_state['next_wav_path'] = unique_wav
        
        full_mp3_path = os.path.join(MUSIC_ROOT_DIR, next_track_path)
        track_info = music_db.get(next_track_path, {})
        
        gain = track_info.get('gain', 0.0)
        cue_point = track_info.get('cue_point', 0.0)
        
        print(f"[Scheduler] Preload '{next_track_path}'")
        p = multiprocessing.Process(target=preload_worker, args=(full_mp3_path, unique_wav, gain, cue_point))
        p.start()

def cleanup_old_wavs():
    current_wav = player_state.get('next_wav_path')
    for f in glob.glob(os.path.join(BASE_DIR, "temp_*.wav")):
        if current_wav and os.path.abspath(f) == os.path.abspath(current_wav): continue
        try: os.remove(f)
        except: pass

def crossfade_to_next():
    global player_state
    now = time.time()
    if now - player_state.get('last_crossfade_time', 0) < 2.0: return
    
    current_idx = player_state['active_channel_id']
    next_idx = 1 - current_idx 
    
    current_channel = pygame.mixer.Channel(current_idx)
    next_channel = pygame.mixer.Channel(next_idx)

    next_path = player_state['next_track_queued']
    wav_path = player_state['next_wav_path']
    
    if not next_path or not wav_path or not os.path.exists(wav_path):
        print("[Automix] Coda vuota. Riprogrammo.")
        schedule_preload()
        return

    try:
        next_sound = pygame.mixer.Sound(wav_path)
    except Exception as e:
        print(f"[Automix] Errore caricamento WAV: {e}")
        return

    # Usiamo fade_duration dal DB se disponibile (default 4.0s)
    # Attenzione: FADE_TIME_MS è una costante globale per ora, per semplicità.
    # In futuro potremmo renderla dinamica leggendo da music_db.
    fade_ms = 4000 
    
    sound_duration_sec = next_sound.get_length()
    play_duration_ms = int((sound_duration_sec * 1000) - fade_ms) if sound_duration_sec > 10 else int(sound_duration_sec * 1000)
    
    if sound_duration_sec < 10: fade_ms = 500

    print(f"[Automix] Crossfade verso '{next_path}' (Dur: {sound_duration_sec:.1f}s)")

    next_channel.set_endevent(CHANNEL_END_EVENTS[next_idx])
    next_channel.play(next_sound, maxtime=play_duration_ms, fade_ms=fade_ms)
    
    if current_channel.get_busy():
        current_channel.fadeout(fade_ms)
    
    player_state['current_track'] = next_path
    player_state['active_channel_id'] = next_idx
    player_state['next_track_queued'] = None
    player_state['next_wav_path'] = None
    player_state['last_crossfade_time'] = now
    
    threading.Thread(target=cleanup_old_wavs).start()
    threading.Thread(target=schedule_preload, daemon=True).start()

def audio_engine_loop():
    while True:
        for event in pygame.event.get():
            if event.type in CHANNEL_END_EVENTS.values():
                channel_id = event.type - pygame.USEREVENT
                if channel_id == player_state['active_channel_id']:
                    crossfade_to_next()
        if player_state['is_playing'] and not player_state['next_track_queued']:
            schedule_preload()
        time.sleep(0.1)

threading.Thread(target=audio_engine_loop, daemon=True).start()

# --- API ---
@app.route('/api/play_folder', methods=['POST'])
def play_folder():
    folder = request.json.get('folder')
    if folder is None: folder = "" 
    try:
        target_dir = validate_path(MUSIC_ROOT_DIR, folder)
        if not os.path.exists(target_dir): return jsonify({"status": "error", "message": "Cartella non trovata"}), 404

        new_playlist = []
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith('.mp3'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, MUSIC_ROOT_DIR).replace('\\', '/')
                    new_playlist.append(rel_path)
        
        if not new_playlist: return jsonify({"status": "error", "message": "Nessun file audio trovato."}), 404

        with audio_lock:
            is_playing = player_state['is_playing']
            player_state['playlist'] = new_playlist
            player_state['queue'] = list(new_playlist)
            player_state['is_playing'] = True
            player_state['is_paused'] = False

        if is_playing:
            end_event_id = CHANNEL_END_EVENTS[player_state['active_channel_id']]
            pygame.event.post(pygame.event.Event(end_event_id))
        else:
            pygame.mixer.stop()
            player_state['next_track_queued'] = None
            player_state['next_wav_path'] = None
            
            first_track = pop_next_track()
            if first_track:
                full_path = os.path.join(MUSIC_ROOT_DIR, first_track)
                tmp_wav = os.path.join(BASE_DIR, f"temp_first_{uuid.uuid4().hex}.wav")
                track_info = music_db.get(first_track, {})
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_mp3(full_path)
                    cue = track_info.get('cue_point', 0.0)
                    gain = track_info.get('gain', 0.0)
                    if cue > 0: audio = audio[int(cue*1000):]
                    if gain != 0: audio = audio.apply_gain(gain)
                    audio.export(tmp_wav, format="wav")
                    
                    player_state['next_track_queued'] = first_track
                    player_state['next_wav_path'] = tmp_wav
                    crossfade_to_next()
                except Exception as e: return jsonify({"status": "error", "message": f"Errore audio: {str(e)}"}), 500
        return jsonify({"status": "ok"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/folders', defaults={'subpath': ''})
@app.route('/api/folders/<path:subpath>')
def api_folders(subpath):
    try: target_dir = validate_path(MUSIC_ROOT_DIR, subpath)
    except PermissionError: abort(403)
    items = []
    has_files = False
    if os.path.exists(target_dir):
        try:
            has_files = any(f.endswith('.mp3') for f in os.listdir(target_dir))
            for d in os.listdir(target_dir):
                p = os.path.join(target_dir, d)
                if os.path.isdir(p) and p.startswith(MUSIC_ROOT_DIR):
                    has_sub = any(os.path.isdir(os.path.join(p, s)) for s in os.listdir(p))
                    items.append({'name': d, 'path': os.path.relpath(p, MUSIC_ROOT_DIR).replace('\\', '/'), 'has_subfolders': has_sub})
        except OSError: pass
    return jsonify({'current_path': subpath, 'has_files': has_files, 'folders': items})

@app.route('/api/next_track', methods=['POST'])
def next_track():
    if player_state['is_playing']:
        end_event_id = CHANNEL_END_EVENTS[player_state['active_channel_id']]
        pygame.event.post(pygame.event.Event(end_event_id))
        return jsonify({"status": "fading"})
    return jsonify({"status": "stopped"})

@app.route('/api/queue')
def get_queue():
    return jsonify({'queue': player_state['queue'], 'count': len(player_state['queue'])})

@app.route('/api/status')
def status():
    track = player_state['current_track']
    info = music_db.get(track, {})
    safe_state = {k: v for k, v in player_state.items() if not callable(v) and k != 'queue' and k != 'playlist'}
    safe_state.update({
        'bpm': info.get('bpm'), 'key': info.get('key'),
        'camelot': info.get('camelot'), 'cue_point': info.get('cue_point'),
        'energy': info.get('energy'), # Mostriamo l'energia
        'queue_count': len(player_state['queue'])
    })
    return jsonify(safe_state)

@app.route('/api/admin/reanalyze', methods=['POST'])
def admin_reanalyze():
    global music_db
    try:
        music_db = {}
        with open(DB_FILE, 'w') as f: json.dump({}, f)
        start_analyzer_process()
        return jsonify({"status": "ok"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/scan_new', methods=['POST'])
def admin_scan_new():
    try:
        start_analyzer_process()
        return jsonify({"status": "ok"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/backup')
def admin_backup():
    if os.path.exists(DB_FILE):
        return send_file(DB_FILE, as_attachment=True, download_name=f"music_db_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    return jsonify({"status": "error"}), 404

@app.route('/api/admin/db_content')
def admin_db_content():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return jsonify(json.load(f))
        except: pass
    return jsonify({})

@app.route('/api/admin/restart', methods=['POST'])
def admin_restart():
    def restart():
        time.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=restart).start()
    return jsonify({"status": "ok"})

@app.route('/api/ping')
def ping(): return jsonify({"status": "pong", "time": time.time()})

@app.route('/api/admin/logs')
def admin_logs():
    if isinstance(sys.stdout, LogCapture): return jsonify({"logs": sys.stdout.get_logs()})
    return jsonify({"logs": ["Log capture not active"]})

@app.route('/api/analysis_status')
def analysis_status():
    if os.path.exists(STATUS_FILE):
        try: with open(STATUS_FILE, 'r') as f: return jsonify(json.load(f))
        except: pass
    return jsonify({'is_running': False, 'progress': 0, 'text': 'In attesa...'})

@app.route('/api/toggle_playback', methods=['POST'])
def toggle_playback():
    if player_state['is_paused']: pygame.mixer.unpause()
    else: pygame.mixer.pause()
    player_state['is_paused'] = not player_state['is_paused']
    return jsonify({"status": "ok"})

@app.route('/')
def index(): return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

if __name__ == '__main__':
    multiprocessing.freeze_support()
    try: from pydub import AudioSegment
    except ImportError: sys.exit(1)
    app.run(host='0.0.0.0', port=5000, threaded=True)