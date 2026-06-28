import pygame
from game_mode import GameMode, GameState
from registry import discover_modes
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT


class MenuMode(GameMode):
    name = "Menu"

    def setup(self, config=None):
        self.modes = discover_modes()
        self.selected = 0
        self.show_history = False
        self.history_scroll = 0
        self.font_title = pygame.font.Font(None, 80)
        self.font_item = pygame.font.Font(None, 52)
        self.font_desc = pygame.font.Font(None, 32)
        self.font_hist = pygame.font.Font(None, 34)
        self.state = GameState.RUNNING

    def handle_input(self, actions):
        if self.show_history:
            if "BACK" in actions or "RED_BUTTON" in actions or "START" in actions:
                self.show_history = False
            elif "UP" in actions:
                self.history_scroll = max(0, self.history_scroll - 1)
            elif "DOWN" in actions:
                self.history_scroll += 1
            return
        if not self.modes:
            return
        if "UP" in actions:
            self.selected = (self.selected - 1) % len(self.modes)
        if "DOWN" in actions:
            self.selected = (self.selected + 1) % len(self.modes)
        if "GREEN_BUTTON" in actions or "SELECT" in actions or "START" in actions:
            self.app.switch_mode(self.modes[self.selected])
        if "RED_BUTTON" in actions:
            mode_cls = self.modes[self.selected]
            if hasattr(mode_cls, "load_history"):
                self.history_data = mode_cls.load_history()
                self.history_scroll = 0
                self.show_history = True

    def draw(self, screen):
        title = self.font_title.render("FIELD OPS", True, COLORS["green"])
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

        hint = self.font_desc.render("[RED] History  [GREEN/ENTER] Play", True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 30))

        if self.show_history:
            self._draw_history(screen)

    def _draw_history(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        title = self.font_item.render("GAME HISTORY", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=20))

        if not self.history_data:
            msg = self.font_hist.render("No games played yet", True, COLORS["grey"])
            screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            return

        header = self.font_hist.render(
            f"{'DATE':<18}{'RESULT':<12}{'TIME':>6}  {'FAILED':>6}  {'CODES':>5}",
            True, COLORS["green"],
        )
        screen.blit(header, (40, 75))
        pygame.draw.line(screen, COLORS["green"], (40, 100), (SCREEN_WIDTH - 40, 100))

        visible = 12
        entries = list(reversed(self.history_data))
        max_scroll = max(0, len(entries) - visible)
        self.history_scroll = min(self.history_scroll, max_scroll)
        page = entries[self.history_scroll:self.history_scroll + visible]

        for i, entry in enumerate(page):
            y = 110 + i * 36
            elapsed = entry.get("elapsed_seconds", 0)
            mins = elapsed // 60
            secs = elapsed % 60
            result = entry.get("result", "?").upper()
            result_color = COLORS["green"] if result == "VICTORY" else COLORS["red"]
            date_surf = self.font_hist.render(f"{entry.get('timestamp', '?'):<18}", True, COLORS["white"])
            screen.blit(date_surf, (40, y))
            result_surf = self.font_hist.render(f"{result:<12}", True, result_color)
            screen.blit(result_surf, (240, y))
            stats = f"{mins:>2}m{secs:02d}s  {entry.get('failed_attempts', 0):>6}  {entry.get('codes_unlocked', 0):>3}/3"
            stats_surf = self.font_hist.render(stats, True, COLORS["white"])
            screen.blit(stats_surf, (420, y))

        if len(entries) > visible:
            scroll_hint = self.font_desc.render(
                f"Showing {self.history_scroll+1}-{self.history_scroll+len(page)} of {len(entries)}  [UP/DOWN to scroll]",
                True, COLORS["grey"],
            )
            screen.blit(scroll_hint, scroll_hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 60))

        close_hint = self.font_desc.render("Press RED / BACK to close", True, COLORS["grey"])
        screen.blit(close_hint, close_hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 30))
