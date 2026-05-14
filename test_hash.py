import sys
import hashlib
from mutagen.mp3 import MP3

def calculate_audio_hash(file_path):
    try:
        audio = MP3(file_path)
        offset = audio.info.audio_offset
        size = audio.info.audio_size
        
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            f.seek(offset)
            # Read in chunks to avoid high memory usage for large files
            bytes_left = size
            while bytes_left > 0:
                chunk_size = min(8192, bytes_left)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_left -= len(chunk)
                
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(calculate_audio_hash(sys.argv[1]))
