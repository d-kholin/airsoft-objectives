import pygame
from pathlib import Path


class SoundManager:
    def __init__(self, sound_dir="assets/sounds"):
        pygame.mixer.init()
        self.sounds = {}
        path = Path(sound_dir)
        if path.exists():
            for f in path.glob("*.wav"):
                self.sounds[f.stem] = pygame.mixer.Sound(f)

    def play(self, name):
        if name in self.sounds:
            self.sounds[name].play()
