import mpv
p = mpv.MPV()
try:
    p.volume = 50
    print(f"Volume is {p.volume}")
except Exception as e:
    print(f"Error: {e}")
