import pygame
from game_mode import GameMode, GameState
from registry import discover_modes
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT


class MenuMode(GameMode):
    name = "Menu"

    def setup(self, config=None):
        self.modes = discover_modes()
        self.selected = 0
        self.font_title = pygame.font.Font(None, 80)
        self.font_item = pygame.font.Font(None, 52)
        self.font_desc = pygame.font.Font(None, 32)
        self.state = GameState.RUNNING

    def handle_input(self, actions):
        if not self.modes:
            return
        if "UP" in actions or "RED_BUTTON" in actions:
            self.selected = (self.selected - 1) % len(self.modes)
        if "DOWN" in actions or "BLUE_BUTTON" in actions:
            self.selected = (self.selected + 1) % len(self.modes)
        if "GREEN_BUTTON" in actions or "SELECT" in actions or "START" in actions:
            self.app.switch_mode(self.modes[self.selected])

    def draw(self, screen):
        title = self.font_title.render("RASPI-BOX", True, COLORS["green"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=20))

        line = pygame.Surface((SCREEN_WIDTH - 80, 2))
        line.fill(COLORS["green"])
        screen.blit(line, (40, 90))

        if not self.modes:
            msg = self.font_item.render("No game modes found", True, COLORS["grey"])
            screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            return

        start_y = 110
        for i, mode_cls in enumerate(self.modes):
            is_selected = i == self.selected
            color = COLORS["green"] if is_selected else COLORS["grey"]
            prefix = "> " if is_selected else "  "
            surf = self.font_item.render(f"{prefix}{mode_cls.name}", True, color)
            screen.blit(surf, (60, start_y + i * 60))

        desc = self.modes[self.selected].description
        if desc:
            surf = self.font_desc.render(desc, True, COLORS["white"])
            screen.blit(surf, surf.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 60))
