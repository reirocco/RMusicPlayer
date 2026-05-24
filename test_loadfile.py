import mpv
import time
p = mpv.MPV()
try:
    p.command('loadfile', './.venv/lib/python3.14/site-packages/pygame/examples/data/house_lo.mp3', 'replace')
    time.sleep(1)
    print("Replace worked")
    p.play('./.venv/lib/python3.14/site-packages/pygame/examples/data/house_lo.mp3')
    # try waiting until ready
    while p.time_pos is None:
        time.sleep(0.01)
    p.time_pos = 2.0
    print(f"Time pos after loop: {p.time_pos}")
except Exception as e:
    print(f"Error: {e}")
