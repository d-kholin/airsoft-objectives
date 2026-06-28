import pygame
from settings import COLORS


class Display:
    def __init__(self, width, height, fullscreen=True):
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("Raspi-Box")
        pygame.mouse.set_visible(False)
        self.width = width
        self.height = height

    def clear(self, color=None):
        self.screen.fill(color or COLORS["bg"])

    def flip(self):
        pygame.display.flip()
