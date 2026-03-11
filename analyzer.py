import os
import json
import warnings
import multiprocessing
import traceback
import time
import sys
import hashlib
from collections import deque

DB_FILE = 'music_db.json'
STATUS_FILE = 'analysis_status.json'
TARGET_DBFS = -14.0 # Target Volume

CAMELOT_MAP = {
    'C': '8B', 'G': '9B', 'D': '10B', 'A': '11B', 'E': '12B', 'B': '1B', 
    'F#': '2B', 'Gb': '2B', 'C#': '3B', 'Db': '3B', 'G#': '4B', 'Ab': '4B', 
    'D#': '5B', 'Eb': '5B', 'A#': '6B', 'Bb': '6B', 'F': '7B',
    'Am': '8A', 'Em': '9A', 'Bm': '10A', 'F#m': '11A', 'Gbm': '11A', 
    'C#m': '12A', 'Dbm': '12A', 'G#m': '1A', 'Abm': '1A', 'D#m': '2A', 'Ebm': '2A', 
    'A#m': '3A', 'Bbm': '3A', 'Fm': '4A', 'Cm': '5A', 'Gm': '6A', 'Dm': '7A'
}

KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def get_music_dir():
    return os.path.join(os.path.expanduser("~"), 'RMusicPlayer')

def calculate_file_hash(file_path):
    try:
        file_size = os.path.getsize(file_path)
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            chunk = f.read(1024 * 1024) 
            sha256_hash.update(chunk)
        sha256_hash.update(str(file_size).encode('utf-8'))
        return sha256_hash.hexdigest()
    except Exception:
        return None

def update_status(progress, text, eta_seconds=None, is_running=True):
    status = {
        'progress': progress, 
        'text': text, 
        'eta_seconds': eta_seconds,
        'is_running': is_running
    }
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception:
        pass 

def _analyze_worker(file_path, return_dict):
    print(f"   [Worker] Inizio processamento di: {os.path.basename(file_path)}", flush=True)
    try:
        import librosa
        import numpy as np
        from pydub import AudioSegment
        warnings.filterwarnings('ignore')
        
        # --- 0. GAIN (Pydub) ---
        try:
            audio = AudioSegment.from_file(file_path)
            current_db = audio.dBFS
            gain = TARGET_DBFS - current_db
        except Exception:
            gain = 0.0

        # --- 1. Librosa Load ---
        try:
            total_duration = librosa.get_duration(path=file_path)
            y, sr = librosa.load(file_path, duration=60, sr=22050)
        except Exception as e:
            return_dict['success'] = False
            return

        if not np.isfinite(y).all(): y = np.nan_to_num(y)
        if len(y) == 0:
            return_dict['success'] = False
            return

        # 2. CUE POINT
        y_trimmed, index = librosa.effects.trim(y, top_db=25)
        cue_point = float(librosa.samples_to_time(index[0], sr=sr))
        
        # 3. BPM
        onset_env = librosa.onset.onset_strength(y=y_trimmed, sr=sr)
        if not np.isfinite(onset_env).all(): onset_env = np.nan_to_num(onset_env)

        try:
            tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            bpm = float(tempo[0] if isinstance(tempo, np.ndarray) else tempo)
        except Exception:
            bpm = 120.0 

        # 4. KEY
        chroma = librosa.feature.chroma_stft(y=y_trimmed, sr=sr)
        if not np.isfinite(chroma).all(): chroma = np.nan_to_num(chroma)
             
        key_idx = np.argmax(np.sum(chroma, axis=1))
        key = KEYS[key_idx]
        camelot = CAMELOT_MAP.get(key, "N/A")

        return_dict['bpm'] = round(bpm, 1)
        return_dict['key'] = key
        return_dict['camelot'] = camelot
        return_dict['cue_point'] = round(cue_point, 3)
        return_dict['duration'] = round(total_duration, 1)
        return_dict['gain'] = round(gain, 2)
        return_dict['success'] = True
        
    except Exception as e:
        print(f"   [Worker] ERRORE: {e}", flush=True)
        return_dict['success'] = False

def safe_analyze_audio(file_path):
    with multiprocessing.Manager() as manager:
        return_dict = manager.dict()
        p = multiprocessing.Process(target=_analyze_worker, args=(file_path, return_dict))
        p.start()
        p.join(timeout=60)
        
        if p.is_alive():
            p.terminate()
            p.join()
            time.sleep(0.1)
            return None, None, None, None, None, None
        
        if p.exitcode != 0:
            time.sleep(0.5)
            return None, None, None, None, None, None
            
        if return_dict.get('success'):
            return return_dict['bpm'], return_dict['key'], return_dict.get('camelot'), return_dict.get('cue_point'), return_dict.get('duration'), return_dict.get('gain')
        else:
            return None, None, None, None, None, None

def build_database():
    base_dir = get_music_dir()
    db = {}
    update_status(0, "Avvio scansione hash...", eta_seconds=None)

    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: db = json.load(f)
        except json.JSONDecodeError: db = {}

    known_hashes = {}
    for path, data in db.items():
        if 'hash' in data: known_hashes[data['hash']] = data

    all_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.mp3'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir).replace('\\', '/')
                all_files.append((full_path, rel_path))

    files_needing_analysis = []
    
    for i, (full_path, rel_path) in enumerate(all_files):
        if i % 20 == 0: 
            update_status(int((i / len(all_files)) * 5), f"Verifica Hash: {os.path.basename(full_path)}")
            
        file_hash = calculate_file_hash(full_path)
        if not file_hash: continue

        # Rianalizza se manca il campo 'gain'
        if file_hash in known_hashes and 'gain' in known_hashes[file_hash]:
            db[rel_path] = known_hashes[file_hash]
            db[rel_path]['hash'] = file_hash
        else:
            files_needing_analysis.append((full_path, rel_path, file_hash))

    total_analysis = len(files_needing_analysis)
    
    if total_analysis > 0:
        print(f"Trovati {total_analysis} file da analizzare.")
        time_window = deque(maxlen=5)
        
        for i, (full_path, rel_path, file_hash) in enumerate(files_needing_analysis):
            start_time = time.time()
            
            avg_time = sum(time_window) / len(time_window) if time_window else 5.0
            eta = int(avg_time * (total_analysis - i))
            progress = 5 + int((i / total_analysis) * 95)
            update_status(progress, f"Analisi ({i+1}/{total_analysis}): {os.path.basename(full_path)}", eta_seconds=eta)
            
            bpm, key, camelot, cue_point, duration, gain = safe_analyze_audio(full_path)
            
            elapsed = time.time() - start_time
            time_window.append(elapsed)
            
            if bpm is not None:
                db[rel_path] = {
                    'bpm': bpm, 'key': key, 'camelot': camelot, 
                    'cue_point': cue_point, 'duration': duration, 'gain': gain, 'hash': file_hash
                }
                known_hashes[file_hash] = db[rel_path]
            else:
                db[rel_path] = {'bpm': 0, 'key': 'Unknown', 'error': True, 'hash': file_hash}

            if (i + 1) % 5 == 0:
                with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
    update_status(100, "Analisi completata!", eta_seconds=0, is_running=False)
    print("Analisi completata!")

if __name__ == "__main__":
    try: multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError: pass
    build_database()