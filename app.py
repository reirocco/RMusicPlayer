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
from analyzer import calculate_audio_hash, read_id3_tags

warnings.filterwarnings('ignore')

# --- LOGGING SYSTEM ---
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
        except Exception:
            pass

    def flush(self):
        try:
            self.original_stream.flush()
        except: pass

    def get_logs(self):
        return list(self.buffer)
    
    def __getattr__(self, name):
        return getattr(self.original_stream, name)

if not isinstance(sys.stdout, LogCapture):
    sys.stdout = LogCapture(sys.stdout)

app = Flask(__name__)

# Configurazione Audio
pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(8)

FADE_TIME_MS = 4000
MIN_DURATION_FOR_CROSSFADE = 10
DB_RELOAD_INTERVAL_SEC = 5

CHANNEL_END_EVENTS = {
    0: pygame.USEREVENT + 0,
    1: pygame.USEREVENT + 1
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_ROOT_DIR = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
DB_FILE = os.path.join(MUSIC_ROOT_DIR, 'music_db.json')
STATUS_FILE = os.path.join(MUSIC_ROOT_DIR, 'analysis_status.json')
ANALYZER_SCRIPT = os.path.join(BASE_DIR, 'analyzer.py')

if not os.path.exists(MUSIC_ROOT_DIR):
    os.makedirs(MUSIC_ROOT_DIR, exist_ok=True)

music_db = {}

# Definizione Stato Player
player_state = {
    'current_track': None, 
    'next_track_queued': None, 
    'next_wav_path': None,
    'folder': None, 
    'is_playing': False, 
    'is_paused': False, 
    'playlist': [],      
    'queue': [],         
    'explicit_queue': [],
    'active_channel_id': 0,
    'last_crossfade_time': 0.0,
    'is_folder_loop_active': False,
    'current_folder_source': None
}

audio_lock = threading.Lock()

def validate_path(base_dir, relative_path):
    if not relative_path:
        return base_dir
    safe_base = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(base_dir, relative_path))
    if not target_path.startswith(safe_base):
        print(f"[SECURITY] Path Traversal blocked: {relative_path}")
        raise PermissionError("Accesso negato")
    return target_path

def clean_startup_temps():
    temps = glob.glob(os.path.join(BASE_DIR, "temp_*.wav")) + \
            glob.glob(os.path.join(BASE_DIR, "temp_*.tmp"))
    if temps:
        print(f"[System] Pulizia di {len(temps)} file temporanei orfani...")
        for f in temps:
            try: os.remove(f)
            except Exception as e: print(f"[System] Impossibile rimuovere temp file: {e}")

clean_startup_temps()

def load_db():
    global music_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: music_db = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[System] Errore caricamento JSON db: {e}")

load_db()

def start_analyzer_process():
    flag_file = os.path.join(MUSIC_ROOT_DIR, 'stop_analysis.flag')
    if os.path.exists(flag_file):
        try: os.remove(flag_file)
        except Exception as e: print(f"[System] Errore rimozione flag file: {e}")
    if os.path.exists(ANALYZER_SCRIPT):
        subprocess.Popen([sys.executable, ANALYZER_SCRIPT])

start_analyzer_process()

def db_reloader():
    last_mtime = 0
    while True:
        if os.path.exists(DB_FILE):
            try:
                mtime = os.path.getmtime(DB_FILE)
                if mtime > last_mtime:
                    load_db()
                    last_mtime = mtime
            except Exception as e:
                print(f"[System] Errore in db_reloader: {e}")
        time.sleep(DB_RELOAD_INTERVAL_SEC)

threading.Thread(target=db_reloader, daemon=True).start()

def are_keys_compatible(key1_camelot, key2_camelot):
    if not key1_camelot or not key2_camelot or "N/A" in [key1_camelot, key2_camelot]: return False
    num1, letter1 = int(key1_camelot[:-1]), key1_camelot[-1]
    num2, letter2 = int(key2_camelot[:-1]), key2_camelot[-1]
    if num1 == num2: return True
    if letter1 == letter2 and (num2 == num1 + 1 or (num1 == 12 and num2 == 1)): return True
    if letter1 == letter2 and (num2 == num1 - 1 or (num1 == 1 and num2 == 12)): return True
    return False

def sort_pool_automix(start_track, pool):
    sorted_queue = []
    current = start_track
    remaining = list(pool)
    
    while remaining:
        if not current:
            chosen = random.choice(remaining)
        else:
            current_track_data = music_db.get(current)
            if not current_track_data:
                chosen = random.choice(remaining)
            else:
                harmonic_matches = [
                    p for p in remaining 
                    if are_keys_compatible(current_track_data.get('camelot'), music_db.get(p, {}).get('camelot'))
                ]
                
                candidates = harmonic_matches if harmonic_matches else remaining
                current_bpm = current_track_data.get('bpm', 120)
                current_energy = current_track_data.get('energy', 5)

                energy_matches = [
                    p for p in candidates
                    if abs(music_db.get(p, {}).get('energy', 5) - current_energy) <= 2
                ]
                if energy_matches: candidates = energy_matches

                candidates.sort(key=lambda p: abs(music_db.get(p, {}).get('bpm', 120) - current_bpm))
                chosen = candidates[0]
                
        sorted_queue.append(chosen)
        remaining.remove(chosen)
        current = chosen
        
    return sorted_queue

def refresh_queue_with_automix():
    folder = player_state.get('current_folder_source')
    if folder is None: return
    
    target_dir = os.path.join(MUSIC_ROOT_DIR, folder) if folder else MUSIC_ROOT_DIR
    if not os.path.exists(target_dir): return
    
    files = []
    current = player_state.get('current_track')
    
    for f in os.listdir(target_dir):
        if f.endswith('.mp3') and not f.startswith('.'):
            full_path = os.path.join(target_dir, f)
            rel_path = os.path.relpath(full_path, MUSIC_ROOT_DIR).replace('\\', '/')
            if rel_path == current:
                continue
            
            db_info = music_db.get(rel_path, {})
            # Aggiungiamo solo brani analizzati e non corrotti
            if db_info and db_info.get('hash') and 'trim_start' in db_info:
                files.append(rel_path)
    
    if files:
        random.shuffle(files)
        with audio_lock:
            print(f"[Automix] Loop Cartella: accodati {len(files)} brani casuali dalla sorgente '{folder}'.")
            player_state['queue'].extend(files)

def pop_next_track():
    global player_state
    
    if player_state['explicit_queue']:
        return player_state['explicit_queue'].pop(0)
    
    if player_state['queue']:
        track = player_state['queue'].pop(0)
        if len(player_state['queue']) == 0 and player_state.get('is_folder_loop_active'):
            threading.Thread(target=refresh_queue_with_automix, daemon=True).start()
        return track
        
    if player_state.get('is_folder_loop_active'):
        print("[Automix] Coda vuota ma Loop attivo. Ricarico sincrono...")
        refresh_queue_with_automix()
        if player_state['queue']:
            return player_state['queue'].pop(0)
            
    if player_state['playlist']:
        print("[Automix] Coda vuota (Loop inattivo). Ricarico e mescolo la playlist originale.")
        start_t = player_state['current_track'] or player_state['playlist'][0]
        player_state['queue'] = sort_pool_automix(start_t, player_state['playlist'])
        if player_state['queue']:
            return player_state['queue'].pop(0)

    return None

def preload_worker(mp3_path, wav_output_path, gain_db=0.0, peak_db=0.0, trim_start=0.0, trim_end=0.0):
    try:
        if sys.platform != "win32": os.nice(19)
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(mp3_path)
        
        start_ms = int(trim_start * 1000) if trim_start > 0 else 0
        end_ms = int(trim_end * 1000) if trim_end > 0 else len(audio)
        
        if start_ms > 0 or end_ms < len(audio):
            audio = audio[start_ms:end_ms]
            
        if gain_db != 0.0:
            if peak_db != 0.0 and (gain_db + peak_db) > 0.0:
                safe_gain = -peak_db
                print(f"[Worker] Gain ridotto da {gain_db}dB a {safe_gain}dB per evitare clipping (Peak: {peak_db}dBFS)")
                gain_db = safe_gain
            audio = audio.apply_gain(gain_db)
            
        tmp_path = wav_output_path + ".tmp"
        audio.export(tmp_path, format="wav")
        os.rename(tmp_path, wav_output_path)
    except Exception as e:
        print(f"[Worker] Errore: {e}")

def schedule_preload():
    with audio_lock:
        if not player_state['playlist'] and not player_state['queue'] and not player_state['explicit_queue']: return
        if player_state['next_track_queued'] and player_state['next_wav_path']: return

        next_track_path = None
        while True:
            next_track_path = pop_next_track()
            if not next_track_path:
                return 

            full_mp3_path = os.path.join(MUSIC_ROOT_DIR, next_track_path)
            if not os.path.exists(full_mp3_path):
                continue

            current_hash = calculate_audio_hash(full_mp3_path)
            id3_data = read_id3_tags(full_mp3_path)
            
            if not id3_data or 'hash' not in id3_data or current_hash != id3_data['hash']:
                print(f"[System] SALTO (Hash fallito): {next_track_path}")
                continue
            
            break
            
        unique_wav = os.path.join(BASE_DIR, f"temp_{uuid.uuid4().hex}.wav")
        player_state['next_track_queued'] = next_track_path
        player_state['next_wav_path'] = unique_wav
        
        track_info = music_db.get(next_track_path, {})
        gain = track_info.get('gain', 0.0)
        peak = track_info.get('peak', 0.0)
        trim_start = track_info.get('trim_start', 0.0)
        trim_end = track_info.get('trim_end', 0.0)
        
        print(f"[Scheduler] Preload di '{next_track_path}' (Gain: {gain}dB, Peak: {peak}dB)")
        p = multiprocessing.Process(target=preload_worker, args=(full_mp3_path, unique_wav, gain, peak, trim_start, trim_end))
        p.start()

def cleanup_old_wavs():
    current_wav = player_state.get('next_wav_path')
    for f in glob.glob(os.path.join(BASE_DIR, "temp_*.wav")):
        if current_wav and os.path.abspath(f) == os.path.abspath(current_wav):
            continue
        try: os.remove(f)
        except Exception as e: print(f"[System] Impossibile pulire wav: {e}")

def crossfade_to_next():
    global player_state
    now = time.time()
    if now - player_state.get('last_crossfade_time', 0) < 2.0: return
    
    current_idx = player_state['active_channel_id']
    next_idx = 1 - current_idx 
    
    current_channel = pygame.mixer.Channel(current_idx)
    next_channel = pygame.mixer.Channel(next_idx)

    next_path = player_state.get('next_track_queued')
    wav_path = player_state.get('next_wav_path')

    if not next_path or not wav_path:
        print("[Automix] Coda di preload vuota. Riprogrammo.")
        schedule_preload()
        return

    if not os.path.exists(wav_path):
        print(f"[Automix] Attendendo che il WAV di '{next_path}' sia pronto...")
        wait_start = time.time()
        while not os.path.exists(wav_path):
            if time.time() - wait_start > 20:
                print("[Automix] Timeout! Il WAV non è stato generato in tempo.")
                return
            time.sleep(0.1)
        print(f"[Automix] WAV pronto dopo {time.time() - wait_start:.1f}s.")

    try:
        next_sound = pygame.mixer.Sound(wav_path)
    except Exception as e:
        print(f"[Automix] Errore caricamento WAV: {e}")
        return

    sound_duration_sec = next_sound.get_length()
    fade_ms = FADE_TIME_MS if sound_duration_sec > MIN_DURATION_FOR_CROSSFADE else 500

    print(f"[Automix] Crossfade verso '{next_path}' (Dur: {sound_duration_sec:.1f}s)")

    next_channel.set_endevent(CHANNEL_END_EVENTS[next_idx])
    next_channel.set_volume(1.0)
    next_channel.play(next_sound, fade_ms=fade_ms)
    
    if current_channel.get_busy():
        current_channel.fadeout(fade_ms)
    
    player_state['current_track'] = next_path
    player_state['active_channel_id'] = next_idx
    player_state['next_track_queued'] = None
    player_state['next_wav_path'] = None
    player_state['last_crossfade_time'] = now
    
    player_state['current_duration_sec'] = sound_duration_sec
    player_state['track_pos_sec'] = 0.0
    player_state['last_play_resume_time'] = now
    
    threading.Thread(target=cleanup_old_wavs).start()
    threading.Thread(target=schedule_preload, daemon=True).start()

def audio_engine_loop():
    while True:
        try:
            for event in pygame.event.get():
                if event.type in CHANNEL_END_EVENTS.values():
                    channel_id = event.type - pygame.USEREVENT
                    if channel_id == player_state['active_channel_id']:
                        if player_state['is_playing']:
                            now = time.time()
                            if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                                print("[Automix] Richiesto passaggio al brano successivo (Skip o Fine brano).")
                                crossfade_to_next()
                                
            if player_state['is_playing'] and not player_state['is_paused']:
                pos_sec = player_state.get('track_pos_sec', 0.0) + (time.time() - player_state.get('last_play_resume_time', time.time()))
                dur_sec = player_state.get('current_duration_sec', 0.0)
                
                fade_sec = FADE_TIME_MS / 1000.0
                if dur_sec > fade_sec and pos_sec >= (dur_sec - fade_sec):
                    now = time.time()
                    if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                        print(f"[Automix] Raggiunto punto di crossfade ({pos_sec:.1f}s / {dur_sec:.1f}s).")
                        crossfade_to_next()
                        
            if player_state['is_playing'] and not player_state['next_track_queued']:
                schedule_preload()
                
        except Exception as e:
            print(f"Errore engine audio: {e}")
            
        time.sleep(0.1)

threading.Thread(target=audio_engine_loop, daemon=True).start()

# --- API ---

@app.route('/api/play_folder', methods=['POST'])
def play_folder():
    folder = request.json.get('folder')
    if folder is None: folder = "" 
    
    try:
        target_dir = validate_path(MUSIC_ROOT_DIR, folder)
        if not os.path.exists(target_dir):
             return jsonify({"status": "error", "message": "Cartella non trovata"}), 404

        new_playlist = []
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith('.mp3') and not file.startswith('.'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, MUSIC_ROOT_DIR).replace('\\', '/')
                    new_playlist.append(rel_path)
        
        if not new_playlist:
            return jsonify({"status": "error", "message": "Nessun file audio trovato."}), 404

        with audio_lock:
            player_state['current_folder_source'] = folder
            is_already_playing = player_state['is_playing']
            player_state['playlist'] = new_playlist
            
            # Mettiamo il primo brano in explicit_queue e pre-ordiniamo il resto
            player_state['explicit_queue'] = [new_playlist[0]]
            if len(new_playlist) > 1:
                player_state['queue'] = sort_pool_automix(new_playlist[0], new_playlist[1:])
            else:
                player_state['queue'] = []
                
            player_state['is_playing'] = True
            player_state['is_paused'] = False

            player_state['next_track_queued'] = None
            player_state['next_wav_path'] = None
            
            first_track = None
            while True:
                first_track = pop_next_track()
                if not first_track: break
                
                full_path = os.path.join(MUSIC_ROOT_DIR, first_track)
                current_hash = calculate_audio_hash(full_path)
                id3_data = read_id3_tags(full_path)
                if not id3_data or 'hash' not in id3_data or current_hash != id3_data['hash']:
                    print(f"[System] SALTO prima traccia corrotta: {first_track}")
                    continue
                break
                
            if first_track:
                full_path = os.path.join(MUSIC_ROOT_DIR, first_track)
                tmp_wav = os.path.join(BASE_DIR, f"temp_first_{uuid.uuid4().hex}.wav")
                
                track_info = music_db.get(first_track, {})
                gain = track_info.get('gain', 0.0)
                peak = track_info.get('peak', 0.0)
                trim_start = track_info.get('trim_start', 0.0)
                trim_end = track_info.get('trim_end', 0.0)
                
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_mp3(full_path)
                    
                    start_ms = int(trim_start * 1000) if trim_start > 0 else 0
                    end_ms = int(trim_end * 1000) if trim_end > 0 else len(audio)
                    
                    if start_ms > 0 or end_ms < len(audio):
                        audio = audio[start_ms:end_ms]
                        
                    if gain != 0:
                        if peak != 0.0 and (gain + peak) > 0.0:
                            safe_gain = -peak
                            print(f"[System] Gain prima traccia ridotto da {gain}dB a {safe_gain}dB per evitare clipping (Peak: {peak}dBFS)")
                            gain = safe_gain
                        audio = audio.apply_gain(gain)
                    audio.export(tmp_wav, format="wav")
                    
                    player_state['next_track_queued'] = first_track
                    player_state['next_wav_path'] = tmp_wav
                    
                    player_state['last_crossfade_time'] = 0
                    if not is_already_playing:
                        pygame.mixer.stop()
                    crossfade_to_next()
                except Exception as e:
                    return jsonify({"status": "error", "message": f"Errore audio: {str(e)}"}), 500
        
        return jsonify({"status": "ok"})
    except PermissionError:
        return jsonify({"status": "error", "message": "Accesso Negato"}), 403
    except Exception as e:
        return jsonify({"status": "error", "message": "Errore interno."}), 500

@app.route('/api/queue/add', methods=['POST'])
def add_to_queue():
    path = request.json.get('path')
    is_folder = request.json.get('is_folder', False)
    if not path: return jsonify({"status": "error", "message": "Nessun percorso fornito"}), 400
        
    try:
        target_dir = validate_path(MUSIC_ROOT_DIR, path)
        if not os.path.exists(target_dir): return jsonify({"status": "error"}), 404
            
        with audio_lock:
            if is_folder:
                new_playlist = []
                for root, dirs, files in os.walk(target_dir):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for file in sorted(files):
                        if file.endswith('.mp3') and not file.startswith('.'):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, MUSIC_ROOT_DIR).replace('\\', '/')
                            new_playlist.append(rel_path)
                if new_playlist:
                    first_track = new_playlist[0]
                    pool = new_playlist[1:]
                    
                    # Svuota la coda e la sostituisce con la nuova cartella
                    player_state['explicit_queue'] = [first_track]
                    player_state['playlist'] = list(new_playlist)
                    player_state['queue'] = sort_pool_automix(first_track, pool)
            else:
                rel_path = os.path.relpath(target_dir, MUSIC_ROOT_DIR).replace('\\', '/')
                player_state['explicit_queue'].append(rel_path)
                
            if not player_state['is_playing'] and not pygame.mixer.get_busy():
                player_state['is_playing'] = True
                player_state['is_paused'] = False
                end_event_id = CHANNEL_END_EVENTS[player_state['active_channel_id']]
                pygame.event.post(pygame.event.Event(end_event_id))
            else:
                old_preloaded = player_state.get('next_track_queued')
                if old_preloaded:
                    if not is_folder:
                        player_state['queue'].insert(0, old_preloaded)
                    
                player_state['next_track_queued'] = None
                player_state['next_wav_path'] = None
                threading.Thread(target=schedule_preload, daemon=True).start()
                
        return jsonify({"status": "ok"})
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/folders', defaults={'subpath': ''})
@app.route('/api/folders/<path:subpath>')
def api_folders(subpath):
    try:
        target_dir = validate_path(MUSIC_ROOT_DIR, subpath)
    except PermissionError: abort(403)

    items = []
    has_files_here = False
    
    if os.path.exists(target_dir):
        try:
            for f in os.listdir(target_dir):
                if f.endswith('.mp3') and not f.startswith('.'):
                    has_files_here = True
                    break
            
            for d in os.listdir(target_dir):
                if d.startswith('.'): continue
                p = os.path.join(target_dir, d)
                if os.path.isdir(p):
                    if not p.startswith(MUSIC_ROOT_DIR): continue
                    has_sub = any(os.path.isdir(os.path.join(p, s)) and not s.startswith('.') for s in os.listdir(p))
                    items.append({
                        'name': d, 
                        'path': os.path.relpath(p, MUSIC_ROOT_DIR).replace('\\', '/'), 
                        'is_folder': True,
                        'has_subfolders': has_sub,
                        'track_count': len([f for f in os.listdir(p) if f.endswith('.mp3') and not f.startswith('.')])
                    })
            
            files_list = []
            for f in sorted(os.listdir(target_dir)):
                if f.endswith('.mp3') and not f.startswith('.'):
                    p = os.path.join(target_dir, f)
                    files_list.append({
                        'name': f,
                        'path': os.path.relpath(p, MUSIC_ROOT_DIR).replace('\\', '/'),
                        'is_folder': False
                    })
            items.extend(files_list)
        except OSError: pass
        
    return jsonify({
        'current_path': subpath,
        'has_files': has_files_here,
        'folders': items
    })

@app.route('/api/next_track', methods=['POST'])
def next_track():
    if player_state['is_playing']:
        end_event_id = CHANNEL_END_EVENTS[player_state['active_channel_id']]
        pygame.event.post(pygame.event.Event(end_event_id))
        return jsonify({"status": "fading"})
    return jsonify({"status": "stopped"})

@app.route('/api/toggle_loop', methods=['POST'])
def toggle_loop():
    with audio_lock:
        player_state['is_folder_loop_active'] = not player_state.get('is_folder_loop_active', False)
        active = player_state['is_folder_loop_active']
        
        # Se è appena stato attivato e la coda è vuota, forziamo il ricaricamento
        if active and len(player_state['queue']) == 0 and player_state.get('current_folder_source') is not None:
            threading.Thread(target=refresh_queue_with_automix, daemon=True).start()
            
    return jsonify({"status": "ok", "is_folder_loop_active": active})

@app.route('/api/queue')
def get_queue():
    ui_explicit = list(player_state['explicit_queue'])
    ui_automix = list(player_state['queue'])
    
    preloaded = player_state.get('next_track_queued')
    if preloaded:
        if ui_explicit:
            ui_explicit.insert(0, preloaded)
        else:
            ui_automix.insert(0, preloaded)
            
    return jsonify({
        'explicit_queue': ui_explicit,
        'automix_queue': ui_automix,
        'count': len(ui_explicit) + len(ui_automix)
    })

@app.route('/api/status')
def status():
    track = player_state['current_track']
    info = music_db.get(track, {})
    # Rimuoviamo oggetti non serializzabili dallo stato
    safe_state = {k: v for k, v in player_state.items() if not callable(v) and k != 'queue' and k != 'playlist'}
    
    preloaded_count = 1 if player_state.get('next_track_queued') else 0
    
    pos = player_state.get('track_pos_sec', 0.0)
    if player_state.get('is_playing') and not player_state.get('is_paused'):
        pos += time.time() - player_state.get('last_play_resume_time', time.time())
        
    safe_state.update({
        'bpm': info.get('bpm'), 'key': info.get('key'),
        'camelot': info.get('camelot'), 'cue_point': info.get('cue_point'),
        'energy': info.get('energy'),
        'queue_count': len(player_state['queue']) + len(player_state['explicit_queue']) + preloaded_count,
        'duration': player_state.get('current_duration_sec', 0.0),
        'position': pos
    })
    return jsonify(safe_state)

@app.route('/api/admin/reanalyze', methods=['POST'])
def admin_reanalyze():
    global music_db
    try:
        music_db = {}
        with open(DB_FILE, 'w') as f: json.dump({}, f)
        start_analyzer_process()
        return jsonify({"status": "ok", "message": "Reset DB e Rianalisi Completa avviata."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/scan_new', methods=['POST'])
def admin_scan_new():
    try:
        start_analyzer_process()
        return jsonify({"status": "ok", "message": "Scansione nuovi file avviata."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/stop_analysis', methods=['POST'])
def admin_stop_analysis():
    flag_file = os.path.join(MUSIC_ROOT_DIR, 'stop_analysis.flag')
    try:
        with open(flag_file, 'w') as f:
            f.write('stop')
        return jsonify({"status": "ok", "message": "Richiesta di interruzione inviata. L'analisi si fermerà al termine del brano corrente."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/backup')
def admin_backup():
    if os.path.exists(DB_FILE):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return send_file(DB_FILE, as_attachment=True, download_name=f"music_db_backup_{timestamp}.json")
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
    def restart_server():
        time.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=restart_server).start()
    return jsonify({"status": "ok", "message": "Riavvio in corso..."})

@app.route('/api/ping')
def ping():
    return jsonify({"status": "pong", "time": time.time()})

@app.route('/api/admin/logs')
def admin_logs():
    if isinstance(sys.stdout, LogCapture):
        return jsonify({"logs": sys.stdout.get_logs()})
    return jsonify({"logs": ["Log capture not active"]})

@app.route('/api/analysis_status')
def analysis_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r') as f: return jsonify(json.load(f))
        except: pass
    return jsonify({'is_running': False, 'progress': 0, 'text': 'In attesa...'})

@app.route('/api/toggle_playback', methods=['POST'])
def toggle_playback():
    if player_state['is_paused']:
        pygame.mixer.unpause()
        player_state['last_play_resume_time'] = time.time()
    else:
        pygame.mixer.pause()
        elapsed = time.time() - player_state.get('last_play_resume_time', time.time())
        player_state['track_pos_sec'] = player_state.get('track_pos_sec', 0.0) + elapsed
    player_state['is_paused'] = not player_state['is_paused']
    return jsonify({"status": "ok"})

@app.route('/')
def index(): return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    multiprocessing.freeze_support()
    try: from pydub import AudioSegment
    except ImportError: sys.exit(1)
    app.run(host='0.0.0.0', port=5000, threaded=True)