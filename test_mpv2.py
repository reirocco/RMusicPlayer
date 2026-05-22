import mpv
import time
p = mpv.MPV()
p.volume = 0
p.play("./.venv/lib/python3.14/site-packages/pygame/examples/data/house_lo.mp3")
time.sleep(1)
print(f"Volume after load: {p.volume}")
