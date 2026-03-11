import os
import json
import librosa
import numpy as np
import warnings

# Ignora i warning di librosa per i file mp3
warnings.filterwarnings('ignore')

DB_FILE = 'music_db.json'
KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def get_music_dir():
    return os.path.join(os.path.expanduser("~"), 'RMusicPlayer')


def analyze_audio(file_path):
    print(f"Analizzo: {os.path.basename(file_path)}")
    try:
        # Carica solo i primi 30 secondi per velocizzare enormemente l'analisi
        y, sr = librosa.load(file_path, duration=30, sr=22050)

        # Calcola BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0] if isinstance(tempo, np.ndarray) else tempo)

        # Calcola la Chiave Armonica (Chromagramma)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_idx = np.argmax(np.sum(chroma, axis=1))
        key = KEYS[key_idx]

        return round(bpm, 1), key
    except Exception as e:
        print(f"Errore con {file_path}: {e}")
        return 120.0, "C"  # Valori di default in caso di errore


def build_database():
    base_dir = get_music_dir()
    db = {}

    # Carica il DB esistente se c'è, per non rifare il lavoro
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            db = json.load(f)

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.mp3'):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir).replace('\\', '/')

                # Analizza solo se non è già nel database
                if rel_path not in db:
                    bpm, key = analyze_audio(full_path)
                    db[rel_path] = {'bpm': bpm, 'key': key}

                    # Salva man mano
                    with open(DB_FILE, 'w') as f:
                        json.dump(db, f, indent=4)

    print("Analisi completata e database aggiornato!")


if __name__ == "__main__":
    print("Avvio scansione musicale...")
    build_database()