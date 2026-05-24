import mpv
import time
import threading

p = mpv.MPV()

def wait_and_seek(ch, ts):
    for _ in range(50):
        if ch.time_pos is not None:
            try:
                ch.time_pos = ts
                print(f"Success setting time_pos to {ts}")
            except Exception as e:
                print(f"Exception while setting time_pos: {e}")
            break
        time.sleep(0.05)

p.play('./.venv/lib/python3.14/site-packages/pygame/examples/data/house_lo.mp3')
threading.Thread(target=wait_and_seek, args=(p, 2.0), daemon=True).start()

time.sleep(2)
print(f"Final pos: {p.time_pos}")
