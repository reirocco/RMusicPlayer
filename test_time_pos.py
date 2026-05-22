import mpv
import time
import sys

p = mpv.MPV()
p.play("./.venv/lib/python3.14/site-packages/pygame/examples/data/house_lo.mp3")
try:
    p.time_pos = 1.0
    print("time_pos succeeded immediately")
except Exception as e:
    print(f"time_pos failed immediately: {e}")

time.sleep(1)
try:
    p.time_pos = 1.0
    print("time_pos succeeded after sleep")
except Exception as e:
    print(f"time_pos failed after sleep: {e}")
