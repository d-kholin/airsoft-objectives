from pathlib import Path

import pygame
from settings import COLORS

WATERMARK_PATH = Path(__file__).parent / "assets" / "images" / "death_monkeys_watermark.png"
WATERMARK_MARGIN = 20


class Display:
    def __init__(self, width, height, fullscreen=True):
        flags = pygame.FULLSCREEN if fullscreen else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption("Field Ops")
        pygame.mouse.set_visible(False)
        self.width = width
        self.height = height
        self._watermark = None
        self._watermark_pos = (0, 0)
        if WATERMARK_PATH.exists():
            self._watermark = pygame.image.load(str(WATERMARK_PATH)).convert_alpha()
            w, h = self._watermark.get_size()
            self._watermark_pos = (width - w - WATERMARK_MARGIN, height - h - WATERMARK_MARGIN)

    def clear(self, color=None):
        self.screen.fill(color or COLORS["bg"])
        if self._watermark:
            self.screen.blit(self._watermark, self._watermark_pos)

    def flip(self):
        pygame.display.flip()
