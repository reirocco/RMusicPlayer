import pygame
import time
pygame.mixer.init()
pygame.mixer.music.load('/home/rocco/RMusicPlayer/MUSICA ITALIANA REMIX/MUSICA ITALIANA 2024 HIT 2024 DEL MOMENTO MIX MUSICA ESTATE 2024.mp3')
pygame.mixer.music.play()
print("Playing...")
for i in range(10):
    time.sleep(1)
    print("Pos:", pygame.mixer.music.get_pos())
