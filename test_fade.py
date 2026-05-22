import mpv
import time
p1 = mpv.MPV()
p1.play("/home/rocco/Documenti/WorkSpace/RMusicPlayer/music/test.mp3") # any mp3
time.sleep(1)
print(f"Volume before: {p1.volume}")
for i in range(10):
    p1.volume = 100 - (i * 10)
    time.sleep(0.1)
print(f"Volume after: {p1.volume}")
