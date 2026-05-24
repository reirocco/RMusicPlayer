import os
import json
import warnings
import multiprocessing
import traceback
import time
import sys
import hashlib
from collections import deque
import datetime

MUSIC_ROOT_DIR = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
DB_FILE = os.path.join(MUSIC_ROOT_DIR, 'music_db.json')
STATUS_FILE = os.path.join(MUSIC_ROOT_DIR, 'analysis_status.json')
FLAG_FILE = os.path.join(MUSIC_ROOT_DIR, 'stop_analysis.flag')
TARGET_LUFS = -14.0 
FORCE_REANALYZE = '--force' in sys.argv

CAMELOT_MAP = {
    'C': '8B', 'G': '9B', 'D': '10B', 'A': '11B', 'E': '12B', 'B': '1B', 
    'F#': '2B', 'Gb': '2B', 'C#': '3B', 'Db': '3B', 'G#': '4B', 'Ab': '4B', 
    'D#': '5B', 'Eb': '5B', 'A#': '6B', 'Bb': '6B', 'F': '7B',
    'Am': '8A', 'Em': '9A', 'Bm': '10A', 'F#m': '11A', 'Gbm': '11A', 
    'C#m': '12A', 'Dbm': '12A', 'G#m': '1A', 'Abm': '1A', 'D#m': '2A', 'Ebm': '2A', 
    'A#m': '3A', 'Bbm': '3A', 'Fm': '4A', 'Cm': '5A', 'Gm': '6A', 'Dm': '7A'
}

KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

from mutagen.id3 import ID3, TBPM, TKEY, TXXX
from mutagen.mp3 import MP3

def calculate_audio_hash(file_path):
    try:
        audio = MP3(file_path)
        offset = audio.info.frame_offset
        
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            f.seek(offset)
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"[Worker] Errore calcolo hash per {file_path}: {e}")
        return None

def delete_rmusic_tags(file_path):
    try:
        try:
            audio = ID3(file_path)
        except Exception:
            return
            
        changed = False
        to_delete = []
        
        # Elimina TBPM e TKEY
        if 'TBPM' in audio:
            to_delete.append('TBPM')
        if 'TKEY' in audio:
            to_delete.append('TKEY')
            
        # Elimina i TXXX creati da noi
        for tag in audio.getall('TXXX'):
            if tag.desc and (tag.desc.startswith('RMusic_') or tag.desc.startswith('X-')):
                to_delete.append(f"TXXX:{tag.desc}")
                
        for key in to_delete:
            if key in audio:
                audio.delall(key)
                changed = True
                
        if changed:
            audio.save(file_path, v2_version=3)
    except Exception as e:
        print(f"[Worker] Errore cancellazione tag per {file_path}: {e}")

def read_id3_tags(file_path):
    try:
        from mutagen import File
        audio_file = File(file_path)
        if audio_file is None or audio_file.tags is None:
            return None
            
        audio = audio_file.tags
        data = {}
        
        bpm_frames = audio.getall('TBPM')
        if bpm_frames: data['bpm'] = float(bpm_frames[0].text[0])
        
        key_frames = audio.getall('TKEY')
        if key_frames: data['key'] = key_frames[0].text[0]
        
        camelot = audio.getall('TXXX:RMusic_Camelot')
        if camelot: data['camelot'] = camelot[0].text[0]
        
        energy = audio.getall('TXXX:RMusic_Energy')
        if energy: data['energy'] = int(float(energy[0].text[0]))
        
        cue_point = audio.getall('TXXX:RMusic_CuePoint')
        if cue_point: data['cue_point'] = float(cue_point[0].text[0])
        
        gain = audio.getall('TXXX:X-REPLAYGAIN-TRACK')
        if gain: data['gain'] = float(gain[0].text[0])
        else:
            old_gain = audio.getall('TXXX:RMusic_Gain')
            if old_gain: data['gain'] = float(old_gain[0].text[0])
            
        peak = audio.getall('TXXX:X-REPLAYGAIN-PEAK')
        if peak: data['peak'] = float(peak[0].text[0])
        
        hash_tag = audio.getall('TXXX:X-ANALYSIS-HASH')
        if hash_tag: data['hash'] = hash_tag[0].text[0]
        
        timestamp_tag = audio.getall('TXXX:X-ANALYSIS-TIMESTAMP')
        if timestamp_tag: data['timestamp'] = timestamp_tag[0].text[0]
        
        trim_start = audio.getall('TXXX:X-TRIM-START')
        if trim_start: data['trim_start'] = float(trim_start[0].text[0])
        
        trim_end = audio.getall('TXXX:X-TRIM-END')
        if trim_end: data['trim_end'] = float(trim_end[0].text[0])
        
        eff_dur = audio.getall('TXXX:X-EFFECTIVE-DURATION')
        if eff_dur: data['effective_duration'] = float(eff_dur[0].text[0])
        
        is_long = audio.getall('TXXX:X-IS-LONG-MIX')
        if is_long and is_long[0].text[0] == 'True':
            data['is_long_mix'] = True
        
        if data.get('is_long_mix'):
            try:
                mp3 = MP3(file_path)
                data['duration'] = round(mp3.info.length, 1)
            except:
                data['duration'] = 0.0
            return data
        
        # Verifica se ci sono i campi essenziali (incluso peak che forza la re-analisi se assente per EBU R128)
        if all(k in data for k in ['bpm', 'key', 'energy', 'cue_point', 'hash', 'trim_start', 'peak']):
            if data.get('gain') == 56.0:
                return None # Forza la rianalisi per i file affetti dal bug del regex ebur128
            try:
                mp3 = MP3(file_path)
                data['duration'] = round(mp3.info.length, 1)
            except:
                data['duration'] = 0.0
            return data
        return None
    except Exception:
        return None

def write_id3_tags(file_path, data):
    try:
        try:
            audio = ID3(file_path)
        except Exception:
            audio = ID3()
            
        audio.add(TBPM(encoding=3, text=str(data.get('bpm', ''))))
        audio.add(TKEY(encoding=3, text=str(data.get('key', ''))))
        audio.add(TXXX(encoding=3, desc='RMusic_Camelot', text=str(data.get('camelot', ''))))
        audio.add(TXXX(encoding=3, desc='RMusic_Energy', text=str(data.get('energy', ''))))
        audio.add(TXXX(encoding=3, desc='RMusic_CuePoint', text=str(data.get('cue_point', ''))))
        audio.add(TXXX(encoding=3, desc='X-REPLAYGAIN-TRACK', text=str(data.get('gain', '0.0'))))
        audio.add(TXXX(encoding=3, desc='X-REPLAYGAIN-PEAK', text=str(data.get('peak', '0.0'))))
        audio.add(TXXX(encoding=3, desc='X-ANALYSIS-HASH', text=str(data.get('hash', ''))))
        audio.add(TXXX(encoding=3, desc='X-ANALYSIS-TIMESTAMP', text=str(data.get('timestamp', ''))))
        audio.add(TXXX(encoding=3, desc='X-TRIM-START', text=str(data.get('trim_start', '0.0'))))
        audio.add(TXXX(encoding=3, desc='X-TRIM-END', text=str(data.get('trim_end', '0.0'))))
        audio.add(TXXX(encoding=3, desc='X-EFFECTIVE-DURATION', text=str(data.get('effective_duration', '0.0'))))
        audio.add(TXXX(encoding=3, desc='X-IS-LONG-MIX', text=str(data.get('is_long_mix', 'False'))))
        
        audio.save(file_path, v2_version=3)
    except Exception as e:
        print(f"Errore salvataggio ID3 su {file_path}: {e}")

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
    except Exception as e:
        print(f"[System] Impossibile aggiornare status file: {e}")

def _analyze_worker(file_path, q):
    return_dict = {}
    print(f"   [Worker] Inizio processamento di: {os.path.basename(file_path)}", flush=True)
    try:
        from mutagen.mp3 import MP3
        duration_sec = 0.0
        try:
            duration_sec = MP3(file_path).info.length
        except:
            pass
            
        if duration_sec > 300.0:
            print(f"   [Worker] Mix lungo rilevato ({duration_sec:.1f}s). Analisi bypassata.", flush=True)
            return_dict['duration'] = round(duration_sec, 1)
            return_dict['is_long_mix'] = True
            return_dict['success'] = True
            q.put(return_dict)
            return

        # --- 0. DURATION (Mutagen) ---
        # duration_sec is already calculated by Mutagen above
        trim_start_sec = 0.0
        trim_end_sec = duration_sec
        effective_duration = duration_sec

        # --- 0.5 EBU R128 LOUDNESS NORMALIZATION & SILENCE DETECT (FFmpeg) ---
        try:
            import subprocess, re
            cmd = ['ffmpeg', '-nostats', '-i', file_path, '-filter_complex', '[0:a]silencedetect=noise=-50dB:d=0.5[a];[a]ebur128=peak=true', '-f', 'null', '-']
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            
            i_matches = re.findall(r'I:\s+([-\d\.]+)\s+LUFS', output)
            peak_match = re.search(r'Peak:\s+([-\d\.]+)\s+dBFS', output)
            
            if i_matches and peak_match:
                i_lufs = float(i_matches[-1])
                peak = float(peak_match.group(1))
                gain = TARGET_LUFS - i_lufs
            else:
                gain = 0.0
                peak = 0.0
                
            silence_starts = re.findall(r'silence_start:\s+([-\d\.]+)', output)
            silence_ends = re.findall(r'silence_end:\s+([-\d\.]+)', output)
            
            if silence_starts and silence_ends and float(silence_starts[0]) <= 0.1:
                trim_start_sec = float(silence_ends[0])
                
            if silence_starts:
                last_start = float(silence_starts[-1])
                if duration_sec > 0 and (duration_sec - last_start) < 15.0:
                    trim_end_sec = last_start
                    
            effective_duration = trim_end_sec - trim_start_sec
            
        except Exception as e:
            print(f"   [Worker] Errore FFmpeg: {e}")
            gain = 0.0
            peak = 0.0

        # --- 1. Aubio Source (Primi 60s per BPM/Key/Energy) ---
        import numpy as np
        import aubio
        
        sr = 44100
        win_s = 512
        hop_s = win_s // 2
        
        try:
            s = aubio.source(file_path, sr, hop_s)
        except Exception as e:
            print(f"   [Worker] Errore aubio.source: {e}")
            return_dict['success'] = False
            q.put(return_dict)
            return
            
        tempo_o = aubio.tempo("default", win_s, hop_s, sr)
        pitch_o = aubio.pitch("yin", win_s, hop_s, sr)
        pitch_o.set_unit("midi")
        pitch_o.set_tolerance(0.8)
        
        beats = []
        pitches = []
        sum_rms = 0.0
        total_frames = 0
        
        max_blocks = int((60.0 * sr) / hop_s)
        blocks_read = 0
        
        while True:
            samples, read = s()
            if read < hop_s:
                samples = np.pad(samples, (0, hop_s - read), mode='constant')
                
            if tempo_o(samples):
                beats.append(tempo_o.get_last_s())
                
            pitch = pitch_o(samples)[0]
            if pitch > 0:
                pitches.append(pitch)
                
            sum_rms += np.sum(samples ** 2)
            total_frames += read
            blocks_read += 1
            
            if blocks_read >= max_blocks or read < hop_s:
                break
                
        if total_frames == 0:
            return_dict['success'] = False
            q.put(return_dict)
            return

        # --- 2. SMART CUE POINT (Beat Detection) ---
        cue_point = beats[0] if beats else 0.0
        if cue_point > 15.0:
            cue_point = 0.0
        cue_point = max(0.0, cue_point - 0.05)

        # --- 3. BPM ---
        if len(beats) > 1:
            intervals = np.diff(beats)
            median_interval = np.median(intervals)
            bpm = 60.0 / median_interval if median_interval > 0 else 120.0
        else:
            bpm = tempo_o.get_bpm()
            if bpm == 0: bpm = 120.0

        # --- 4. KEY ---
        if pitches:
            pitch_classes = [int(round(p)) % 12 for p in pitches]
            counts = np.bincount(pitch_classes)
            key_idx = np.argmax(counts)
            key = KEYS[key_idx]
        else:
            key = 'C'
            
        camelot = CAMELOT_MAP.get(key, "N/A")

        # --- 5. ENERGY LEVEL ---
        mean_rms = np.sqrt(sum_rms / total_frames) if total_frames > 0 else 0
        energy = int(np.clip((mean_rms - 0.02) / (0.25 - 0.02) * 9 + 1, 1, 10))

        return_dict['bpm'] = round(bpm, 1)
        return_dict['key'] = key
        return_dict['camelot'] = camelot
        return_dict['cue_point'] = round(cue_point, 3)
        return_dict['duration'] = round(duration_sec, 1)
        return_dict['trim_start'] = round(trim_start_sec, 3)
        return_dict['trim_end'] = round(trim_end_sec, 3)
        return_dict['effective_duration'] = round(effective_duration, 1)
        return_dict['gain'] = round(gain, 2)
        return_dict['peak'] = round(peak, 2)
        return_dict['energy'] = energy
        return_dict['success'] = True
        q.put(return_dict)
        
    except Exception as e:
        print(f"   [Worker] ERRORE: {e}", flush=True)
        return_dict['success'] = False
        q.put(return_dict)

def safe_analyze_audio(file_path, current_hash):
    if FORCE_REANALYZE:
        delete_rmusic_tags(file_path)
    else:
        cached = read_id3_tags(file_path)
        if cached and cached.get('hash') == current_hash:
            cached['_from_cache'] = True
            return cached

    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_analyze_worker, args=(file_path, q))
    p.start()
    p.join(timeout=600) # 10 minuti per i mix lunghi
    
    if p.is_alive():
        p.terminate()
        p.join()
        time.sleep(0.1)
        return None
    
    if p.exitcode != 0:
        time.sleep(0.5)
        return None
        
    try:
        if not q.empty():
            return_dict = q.get_nowait()
            if return_dict.get('success'):
                return return_dict
    except:
        pass
    return None

def build_database():
    base_dir = MUSIC_ROOT_DIR
    if os.path.exists(FLAG_FILE):
        try: os.remove(FLAG_FILE)
        except Exception as e: print(f"[System] Errore rimozione flag: {e}")
    db = {}
    update_status(0, "Lettura metadati ID3...", eta_seconds=None)

    json_missing = False
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: db = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[System] JSON corrotto o illeggibile: {e}")
            db = {}
            json_missing = True
    else:
        json_missing = True
        
    if json_missing:
        print("[System] music_db.json mancante o corrotto. Verrà ricostruito l'indice dai metadati dei file (nessuna ri-analisi necessaria se l'hash combacia).")

    # Non usiamo più known_hashes perché ci fidiamo dei file MP3
    # Manteniamo la cache in RAM (db) e controlliamo fisicamente l'ID3 per i file.
    
    all_files = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            if file.endswith('.mp3') and not file.startswith('.'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir).replace('\\', '/')
                all_files.append((full_path, rel_path))

    files_needing_analysis = []
    
    for i, (full_path, rel_path) in enumerate(all_files):
        if FORCE_REANALYZE:
            files_needing_analysis.append((full_path, rel_path, None))
        elif rel_path not in db:
            files_needing_analysis.append((full_path, rel_path, None))

    all_rel_paths = set(rel_path for _, rel_path in all_files)
    keys_to_remove = [k for k in db.keys() if k not in all_rel_paths]
    for k in keys_to_remove:
        del db[k]

    total_analysis = len(files_needing_analysis)
    
    if total_analysis > 0:
        print(f"Trovati {total_analysis} file da analizzare.")
        time_window = deque(maxlen=5)
        
        for i, (full_path, rel_path, current_hash) in enumerate(files_needing_analysis):
            if os.path.exists(FLAG_FILE):
                print("Richiesta di interruzione ricevuta!", flush=True)
                try: os.remove(FLAG_FILE)
                except Exception as e: print(f"[System] Errore rimozione flag: {e}")
                with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
                update_status(progress if 'progress' in locals() else 0, "Analisi interrotta dall'utente.", is_running=False)
                return

            start_time = time.time()
            
            if current_hash is None:
                current_hash = calculate_audio_hash(full_path)
            
            avg_time = sum(time_window) / len(time_window) if time_window else 5.0
            eta = int(avg_time * (total_analysis - i))
            progress = 5 + int((i / total_analysis) * 95)
            update_status(progress, f"Analisi ({i+1}/{total_analysis}): {os.path.basename(full_path)}", eta_seconds=eta)
            
            result = safe_analyze_audio(full_path, current_hash)
            
            elapsed = time.time() - start_time
            time_window.append(elapsed)
            
            if result:
                # Pulizia: rimuovi chiavi interne del worker se presenti
                if 'success' in result: del result['success']
                
                is_from_cache = result.pop('_from_cache', False)

                if not is_from_cache:
                    result['hash'] = current_hash
                    result['timestamp'] = datetime.datetime.now().isoformat()
                    # Salva i metadati nel file MP3 solo se nuovo
                    write_id3_tags(full_path, result)
                
                db[rel_path] = result
            else:
                db[rel_path] = {'bpm': 0, 'key': 'Unknown', 'error': True}

            if (i + 1) % 5 == 0:
                with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
    update_status(100, "Avvio verifica volume Mix Lunghi...", eta_seconds=0, is_running=True)
    import subprocess
    import sys
    subprocess.Popen([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'normalizer.py')])
    print("Analisi completata! Passaggio al Normalizzatore.")

if __name__ == "__main__":
    try: multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError: pass
    build_database()