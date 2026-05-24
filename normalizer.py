import os
import json
import time
import uuid
import subprocess
import re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TXXX

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_ROOT_DIR = os.path.join(os.path.expanduser("~"), 'RMusicPlayer')
STATUS_FILE = os.path.join(MUSIC_ROOT_DIR, 'analysis_status.json')
TARGET_LUFS = -14.0
THRESHOLD_LUFS = -15.0

def mark_as_normalized(file_path):
    try:
        try:
            audio = ID3(file_path)
        except Exception:
            audio = ID3()
        audio.add(TXXX(encoding=3, desc='X-IS-NORMALIZED', text='True'))
        audio.save(file_path, v2_version=3)
    except Exception as e:
        print(f"[Normalizer] Errore tag ID3 su {file_path}: {e}")

def check_if_normalized(file_path):
    try:
        audio = ID3(file_path)
        for tag in audio.getall("TXXX"):
            if tag.desc == 'X-IS-NORMALIZED' and tag.text[0] == 'True':
                return True
    except: pass
    return False

def update_status(progress, text, is_running=True):
    status = {
        'progress': progress, 
        'text': text, 
        'eta_seconds': None,
        'is_running': is_running
    }
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        print(f"[Normalizer] Errore status: {e}")

def get_duration(file_path):
    try:
        audio = MP3(file_path)
        return audio.info.length
    except:
        return 0.0

def get_lufs(file_path):
    try:
        cmd = ['ffmpeg', '-nostats', '-i', file_path, '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-']
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        i_matches = re.findall(r'I:\s+([-\d\.]+)\s+LUFS', output)
        if i_matches:
            return float(i_matches[-1])
    except Exception as e:
        print(f"[Normalizer] Errore EBU R128 su {os.path.basename(file_path)}: {e}")
    return None

def normalize_file(file_path, gain_db):
    temp_file = os.path.join(BASE_DIR, f"temp_norm_{uuid.uuid4().hex}.mp3")
    try:
        print(f"[Normalizer] Normalizzo {os.path.basename(file_path)} di +{gain_db:.1f}dB...")
        cmd = [
            'ffmpeg', '-y', '-i', file_path,
            '-af', f'volume={gain_db}dB,alimiter=limit=-0.5dB',
            '-c:a', 'libmp3lame', '-b:a', '320k',
            temp_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Sovrascrivi originale
        os.replace(temp_file, file_path)
        mark_as_normalized(file_path)
        print(f"[Normalizer] Completato {os.path.basename(file_path)}")
        return True
    except Exception as e:
        print(f"[Normalizer] Errore conversione {os.path.basename(file_path)}: {e}")
        if os.path.exists(temp_file):
            try: os.remove(temp_file)
            except: pass
        return False

def main():
    print("[Normalizer] Avvio scansione per mix lunghi...")
    update_status(0, "Ricerca mix lunghi...", is_running=True)
    
    mp3_files = []
    for root, dirs, files in os.walk(MUSIC_ROOT_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in files:
            if f.endswith('.mp3') and not f.startswith('.'):
                mp3_files.append(os.path.join(root, f))
                
    total_files = len(mp3_files)
    if total_files == 0:
        update_status(100, "Nessun file trovato.", is_running=False)
        return

    mix_files = []
    
    # 1. Filtra solo i file lunghi
    for i, file_path in enumerate(mp3_files):
        if i % 10 == 0:
            update_status(0, f"Filtro mix lunghi ({i}/{total_files})...", is_running=True)
        dur = get_duration(file_path)
        if dur >= 300.0:
            mix_files.append(file_path)
            
    total_mix = len(mix_files)
    print(f"[Normalizer] Trovati {total_mix} mix lunghi da verificare.")
    
    if total_mix == 0:
        update_status(100, "Nessun mix lungo trovato.", is_running=False)
        return

    # 2. Verifica LUFS e Normalizza
    processed = 0
    normalized_count = 0
    
    for i, file_path in enumerate(mix_files):
        fname = os.path.basename(file_path)
        
        # Check stop flag
        flag_file = os.path.join(MUSIC_ROOT_DIR, 'stop_analysis.flag')
        if os.path.exists(flag_file):
            print("[Normalizer] Ricevuto segnale di stop.")
            os.remove(flag_file)
            update_status(100, "Normalizzazione interrotta.", is_running=False)
            return
            
        if check_if_normalized(file_path):
            continue
            
        progress = int((i / total_mix) * 100)
        update_status(progress, f"Misurazione LUFS: {fname[:30]}...", is_running=True)
        
        lufs = get_lufs(file_path)
        if lufs is not None:
            if lufs < THRESHOLD_LUFS:
                gain = TARGET_LUFS - lufs
                update_status(progress, f"Amplifico +{gain:.1f}dB: {fname[:30]}...", is_running=True)
                success = normalize_file(file_path, gain)
                if success:
                    normalized_count += 1
            else:
                # Se è già a posto (es. -12 LUFS), taggalo così la prossima volta skippa sùbito
                mark_as_normalized(file_path)
        
        processed += 1

    update_status(100, f"Completato! {normalized_count} mix normalizzati.", is_running=False)
    time.sleep(3)
    update_status(100, "In attesa...", is_running=False)

if __name__ == "__main__":
    main()
