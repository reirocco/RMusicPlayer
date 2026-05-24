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
import mpv
import warnings
from analyzer import calculate_audio_hash, read_id3_tags

warnings.filterwarnings('ignore')

from logger_config import core_logger, flask_logger, memory_handler

app = Flask(__name__)

import logging
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.handlers = flask_logger.handlers
app.logger.setLevel(flask_logger.level)

@app.errorhandler(Exception)
def handle_exception(e):
    flask_logger.exception(f"Unhandled Exception: {e}")
    return jsonify(error=str(e)), 500


# Configurazione Audio
mpv_player_a = mpv.MPV(ytdl=False, video=False)
mpv_player_b = mpv.MPV(ytdl=False, video=False)
channels = {0: mpv_player_a, 1: mpv_player_b}

FADE_TIME_MS = 4000
MIN_DURATION_FOR_CROSSFADE = 10
DB_RELOAD_INTERVAL_SEC = 5

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_ROOT_DIR = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
DB_FILE = os.path.join(MUSIC_ROOT_DIR, 'music_db.json')
STATUS_FILE = os.path.join(MUSIC_ROOT_DIR, 'analysis_status.json')
ANALYZER_SCRIPT = os.path.join(BASE_DIR, 'analyzer.py')
NORMALIZER_SCRIPT = os.path.join(BASE_DIR, 'normalizer.py')

if not os.path.exists(MUSIC_ROOT_DIR):
    os.makedirs(MUSIC_ROOT_DIR, exist_ok=True)

music_db = {}

# Definizione Stato Player
player_state = {
    'current_track': None, 
    'next_track_queued': None, 
    'folder': None, 
    'is_playing': False, 
    'is_paused': False, 
    'playlist': [],      
    'queue': [],         
    'explicit_queue': [],
    'active_channel_id': 0,
    'last_crossfade_time': 0.0,
    'crossfade_id': 0,
    'is_folder_loop_active': False,
    'current_folder_source': None,
}

audio_lock = threading.Lock()

def validate_path(base_dir, relative_path):
    if not relative_path:
        return base_dir
    safe_base = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(base_dir, relative_path))
    if not target_path.startswith(safe_base):
        core_logger.info(f"[SECURITY] Path Traversal blocked: {relative_path}")
        raise PermissionError("Accesso negato")
    return target_path



def load_db():
    global music_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: music_db = json.load(f)
        except json.JSONDecodeError as e:
            core_logger.error(f"[System] Errore caricamento JSON db: {e}")

load_db()

def start_analyzer_process(force=False):
    flag_file = os.path.join(MUSIC_ROOT_DIR, 'stop_analysis.flag')
    if os.path.exists(flag_file):
        try: os.remove(flag_file)
        except Exception as e: core_logger.error(f"[System] Errore rimozione flag file: {e}")
    if os.path.exists(ANALYZER_SCRIPT):
        args = [sys.executable, ANALYZER_SCRIPT]
        if force: args.append('--force')
        subprocess.Popen(args)

start_analyzer_process()

def start_normalizer_process():
    flag_file = os.path.join(MUSIC_ROOT_DIR, 'stop_analysis.flag')
    if os.path.exists(flag_file):
        try: os.remove(flag_file)
        except Exception as e: core_logger.error(f"[System] Errore rimozione flag file: {e}")
    if os.path.exists(NORMALIZER_SCRIPT):
        subprocess.Popen([sys.executable, NORMALIZER_SCRIPT])

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
                core_logger.error(f"[System] Errore in db_reloader: {e}")
        time.sleep(DB_RELOAD_INTERVAL_SEC)

threading.Thread(target=db_reloader, daemon=True).start()

def are_keys_compatible(key1_camelot, key2_camelot):
    if not key1_camelot or not key2_camelot or "N/A" in [key1_camelot, key2_camelot]: return False
    try:
        num1, letter1 = int(key1_camelot[:-1]), key1_camelot[-1]
        num2, letter2 = int(key2_camelot[:-1]), key2_camelot[-1]
    except ValueError:
        return False
    if num1 == num2: return True
    if letter1 == letter2 and (num2 == num1 + 1 or (num1 == 12 and num2 == 1)): return True
    if letter1 == letter2 and (num2 == num1 - 1 or (num1 == 1 and num2 == 12)): return True
    return False

def sort_pool_automix(start_track, pool):
    sorted_queue = []
    current = start_track
    remaining = list(pool)
    
    db_cache = {p: music_db.get(p, {}) for p in remaining}
    if current:
        db_cache[current] = music_db.get(current, {})
    
    while remaining:
        if not current:
            chosen = random.choice(remaining)
        else:
            current_track_data = db_cache.get(current, {})
            current_camelot = current_track_data.get('camelot')
            current_bpm = current_track_data.get('bpm', 120)
            current_energy = current_track_data.get('energy', 5)

            candidates = []
            if current_camelot and current_camelot != "N/A":
                candidates = [
                    p for p in remaining 
                    if are_keys_compatible(current_camelot, db_cache[p].get('camelot'))
                ]
            
            if not candidates:
                candidates = remaining
                
            energy_matches = [
                p for p in candidates
                if abs(db_cache[p].get('energy', 5) - current_energy) <= 2
            ]
            if energy_matches: 
                candidates = energy_matches

            chosen = min(candidates, key=lambda p: abs(db_cache[p].get('bpm', 120) - current_bpm))
                
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
    
    for root, dirs, f_list in os.walk(target_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in f_list:
            if f.endswith('.mp3') and not f.startswith('.'):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, MUSIC_ROOT_DIR).replace('\\', '/')
                if rel_path == current:
                    continue
                
                files.append(rel_path)
    
    if files:
        random.shuffle(files)
        with audio_lock:
            core_logger.info(f"[Automix] Loop Cartella: accodati {len(files)} brani casuali dalla sorgente '{folder}'.")
            player_state['queue'].extend(files)

def pop_next_track():
    global player_state
    
    if player_state['explicit_queue']:
        player_state['next_track_source'] = 'explicit'
        return player_state['explicit_queue'].pop(0)
    
    if player_state['queue']:
        player_state['next_track_source'] = 'automix'
        track = player_state['queue'].pop(0)
        if len(player_state['queue']) == 0 and player_state.get('is_folder_loop_active'):
            threading.Thread(target=refresh_queue_with_automix, daemon=True).start()
        return track
        
    if player_state.get('is_folder_loop_active'):
        core_logger.info("[Automix] Coda vuota ma Loop attivo. Ricarico sincrono...")
        refresh_queue_with_automix()
        if player_state['queue']:
            player_state['next_track_source'] = 'automix'
            return player_state['queue'].pop(0)
            
    if player_state['playlist']:
        core_logger.info("[Automix] Coda vuota (Loop inattivo). Ricarico e mescolo la playlist originale.")
        start_t = player_state['current_track'] or player_state['playlist'][0]
        player_state['queue'] = sort_pool_automix(start_t, player_state['playlist'])
        if player_state['queue']:
            player_state['next_track_source'] = 'automix'
            return player_state['queue'].pop(0)

    player_state['next_track_source'] = None
    return None



def schedule_preload():
    with audio_lock:
        if not player_state['playlist'] and not player_state['queue'] and not player_state['explicit_queue']: return
        if player_state.get('next_track_queued'): return

        next_track_path = pop_next_track()
        if not next_track_path: return

        player_state['next_track_queued'] = next_track_path
        core_logger.info(f"[Scheduler] Prossima traccia in coda: '{next_track_path}'")



def crossfade_to_next():
    global player_state
    now = time.time()
    core_logger.debug(f"\n--- CROSSFADE START ({now}) ---")
    if now - player_state.get('last_crossfade_time', 0) < 2.0: 
        core_logger.debug(f"Debounce: < 2.0s since last crossfade.")
        return
    
    current_idx = player_state['active_channel_id']
    next_idx = 1 - current_idx 
    
    current_channel = channels[current_idx]
    next_channel = channels[next_idx]

    next_path = player_state.get('next_track_queued')
    core_logger.debug(f"next_track_queued is: {next_path}")
    if not next_path:
        core_logger.debug(f"next_path is None, scheduling preload and returning.")
        player_state['last_crossfade_time'] = now
        schedule_preload()
        return

    full_mp3_path = os.path.join(MUSIC_ROOT_DIR, next_path)
    track_info = music_db.get(next_path, {})
    duration = track_info.get('duration', 0.0)
    trim_end = track_info.get('trim_end', duration)
    if trim_end <= 0.1:
        try:
            from mutagen.mp3 import MP3
            trim_end = MP3(full_mp3_path).info.length
        except:
            trim_end = duration if duration > 0 else 300.0
    
    gain = track_info.get('gain', 0.0)
    trim_start = track_info.get('trim_start', 0.0)
    
    fade_sec = FADE_TIME_MS / 1000.0 if duration > MIN_DURATION_FOR_CROSSFADE else 0.5
    
    core_logger.info(f"[Automix] Crossfade verso '{next_path}' (Dur: {duration:.1f}s, Gain: {gain}dB)")
    
    if gain != 0.0:
        next_channel.command('set', 'options/af', f'volume={gain}dB')
    else:
        next_channel.command('set', 'options/af', 'volume=0dB')
        
    try:
        core_logger.debug(f"Calling next_channel.play({full_mp3_path})")
        next_channel.pause = False
        next_channel.play(full_mp3_path)
        core_logger.debug(f"play() successful.")
        if trim_start > 0:
            def wait_and_seek(ch, ts):
                for _ in range(50):
                    if ch.time_pos is not None:
                        try:
                            ch.time_pos = ts
                        except: pass
                        break
                    time.sleep(0.05)
            threading.Thread(target=wait_and_seek, args=(next_channel, trim_start), daemon=True).start()
    except Exception as e:
        core_logger.debug(f"Exception in play(): {e}")
        core_logger.error(f"[Automix] Errore durante play(): {e}")
        
    player_state['crossfade_id'] += 1
    current_cf_id = player_state['crossfade_id']

    def fade_in_out(curr, nxt, duration_sec, cf_id):
        steps = 20
        sleep_time = duration_sec / steps
        for i in range(steps):
            if player_state.get('crossfade_id') != cf_id:
                return # Stop thread if a new crossfade started
            vol_out = max(0, 100 - int((i / steps) * 100))
            vol_in = min(100, int((i / steps) * 100))
            try:
                curr.volume = vol_out
                nxt.volume = vol_in
            except: pass
            time.sleep(sleep_time)
            
        if player_state.get('crossfade_id') == cf_id:
            try:
                curr.stop()
                curr.volume = 100
            except: pass

    threading.Thread(target=fade_in_out, args=(current_channel, next_channel, fade_sec, current_cf_id), daemon=True).start()
    
    player_state['current_track'] = next_path
    player_state['active_channel_id'] = next_idx
    player_state['next_track_queued'] = None
    player_state['last_crossfade_time'] = now
    player_state['current_duration_sec'] = trim_end
    player_state['last_play_resume_time'] = now
    player_state['track_pos_sec'] = trim_start
    player_state['is_paused'] = False
    
    threading.Thread(target=schedule_preload, daemon=True).start()
    core_logger.debug(f"CROSSFADE FINISHED (Scheduled preload).")

def audio_engine_loop():
    while True:
        try:
            if player_state['is_playing'] and not player_state['is_paused']:
                current_channel = channels[player_state['active_channel_id']]
                
                # Check MPV properties
                if current_channel.time_pos is not None:
                    pos_sec = current_channel.time_pos
                    dur_sec = player_state.get('current_duration_sec', 0.0)
                    fade_sec = FADE_TIME_MS / 1000.0
                    
                    if dur_sec > fade_sec and pos_sec >= (dur_sec - fade_sec):
                        now = time.time()
                        if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                            core_logger.info(f"[Automix] Raggiunto punto di crossfade ({pos_sec:.1f}s / {dur_sec:.1f}s).")
                            crossfade_to_next()
                
                # Fallback se ha smesso di suonare improvvisamente
                if getattr(current_channel, 'eof_reached', False) or getattr(current_channel, 'core_idle', False):
                    now = time.time()
                    if now - player_state.get('last_crossfade_time', 0) >= 2.0:
                        crossfade_to_next()

            if player_state['is_playing'] and not player_state.get('next_track_queued'):
                schedule_preload()
                
        except Exception as e:
            pass
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
            
            
            first_track = pop_next_track()
                
            if first_track:
                full_path = os.path.join(MUSIC_ROOT_DIR, first_track)
                
                
                track_info = music_db.get(first_track, {})
                duration = track_info.get('duration', 0.0)
                gain = track_info.get('gain', 0.0)
                peak = track_info.get('peak', 0.0)
                trim_start = track_info.get('trim_start', 0.0)
                trim_end = track_info.get('trim_end', 0.0)
                
                try:
                    player_state['next_track_queued'] = first_track
                    player_state['last_crossfade_time'] = 0
                    
                    
                    if not is_already_playing:
                        channels[player_state['active_channel_id']].stop()
                    
                    core_logger.info(f"[Automix] Avvio prima traccia: {first_track}")
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
                
            if not player_state['is_playing']:
                player_state['is_playing'] = True
                player_state['is_paused'] = False
                crossfade_to_next()
            else:
                old_preloaded = player_state.get('next_track_queued')
                if old_preloaded:
                    if not is_folder:
                        player_state['queue'].insert(0, old_preloaded)
                    
                player_state['next_track_queued'] = None
                
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
    try:
        with open('/tmp/rmusic_debug.log', 'a') as logf: logf.write(f"\\n--- API NEXT TRACK (is_playing={player_state['is_playing']}) ---\\n")
        if player_state['is_playing']:
            if player_state['is_paused']:
                with open('/tmp/rmusic_debug.log', 'a') as logf: logf.write(f"Unpausing channel {player_state['active_channel_id']}\\n")
                channels[player_state['active_channel_id']].pause = False
            
            with open('/tmp/rmusic_debug.log', 'a') as logf: logf.write(f"Calling crossfade_to_next()\\n")
            crossfade_to_next()
            with open('/tmp/rmusic_debug.log', 'a') as logf: logf.write(f"crossfade_to_next() returned.\\n")
            return jsonify({"status": "fading"})
        return jsonify({"status": "stopped"})
    except Exception as e:
        with open('/tmp/rmusic_debug.log', 'a') as logf: logf.write(f"CRASH IN NEXT_TRACK: {e}\\n")
        import traceback
        with open('/tmp/rmusic_debug.log', 'a') as logf: logf.write(traceback.format_exc())
        return jsonify({"status": "error"}), 500

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
        source = player_state.get('next_track_source', 'automix')
        if source == 'explicit':
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
    
    if player_state.get('is_playing') and not player_state.get('is_paused'):
        curr = channels[player_state['active_channel_id']]
        if curr.time_pos is not None:
            pos = curr.time_pos
        else:
            pos = 0.0
    else:
        pos = player_state.get('track_pos_sec', 0.0)
        
    safe_state.update({
        'bpm': info.get('bpm'), 'key': info.get('key'),
        'camelot': info.get('camelot'), 'cue_point': info.get('cue_point'),
        'energy': info.get('energy'),
        'queue_count': len(player_state['queue']) + len(player_state['explicit_queue']) + preloaded_count,
        'duration': info.get('effective_duration', player_state.get('current_duration_sec', 0.0)),
        'position': max(0.0, pos - info.get('trim_start', 0.0))
    })
    return jsonify(safe_state)

@app.route('/api/admin/reanalyze', methods=['POST'])
def admin_reanalyze():
    global music_db
    try:
        music_db = {}
        with open(DB_FILE, 'w') as f: json.dump({}, f)
        start_analyzer_process(force=True)
        return jsonify({"status": "ok", "message": "Reset DB e Rianalisi Completa avviata."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/normalize_mixes', methods=['POST'])
def admin_normalize_mixes():
    try:
        start_normalizer_process()
        return jsonify({"status": "ok", "message": "Normalizzazione Mix Lunghi avviata in background."})
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
        return jsonify({"logs": memory_handler.get_logs()})
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
        channels[player_state['active_channel_id']].pause = False
        player_state['last_play_resume_time'] = time.time()
    else:
        channels[player_state['active_channel_id']].pause = True
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
    
    app.run(host='0.0.0.0', port=5000, threaded=True)