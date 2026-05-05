import os
import sys

# Aggiungi la dir corrente per poter importare
sys.path.append(os.getcwd())
import analyzer

file_path = "/home/rocco/RMusicPlayer/Balli di gruppo/Ti Amo Ti Amo - Line Dance ( by  Berta ).mp3"

data = {
    'bpm': 125.0,
    'key': 'Am',
    'camelot': '8A',
    'energy': 8,
    'cue_point': 1.234,
    'gain': -1.5,
    'duration': 210.0
}

print("1. Scrivo i tag ID3...")
analyzer.write_id3_tags(file_path, data)

print("2. Leggo i tag ID3 appena scritti...")
read_data = analyzer.read_id3_tags(file_path)
print(f"Letti: {read_data}")
