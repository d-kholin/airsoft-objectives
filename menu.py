import pygame
from game_mode import GameMode
from registry import discover_modes
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT
from ui import draw_menu_item
from fonts import get_font, char_width

# History table column widths, in monospace character cells:
# DATE, RESULT/WINNER, TIME, col4, col5.
HIST_COL_CHARS = [17, 9, 8, 9, 8]


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
        # Monospace so history columns align by character cell, not by guessing
        # pixel offsets for a proportional font.
        self.font_hist = get_font(28, mono=True)

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
            draw_menu_item(
                screen, self.font_item, mode_cls.name,
                i == self.selected, 60, start_y + i * 60,
            )

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

        is_bomb = self.history_data and "strikes" in self.history_data[0]
        is_dom = self.history_data and "red_hold_time" in self.history_data[0]
        is_missile = self.history_data and "countdown_total" in self.history_data[0]

        # Column x-positions derived from the monospace cell width, so the
        # header and every data row line up by construction.
        left = 40
        cw = char_width(self.font_hist)
        cols = []
        acc = left
        for width in HIST_COL_CHARS:
            cols.append(acc)
            acc += width * cw
        COL_DATE, COL_RESULT, COL_TIME, COL_4, COL_5 = cols

        if is_bomb:
            label_result, label_4, label_5 = "RESULT", "STRIKES", "MODULES"
        elif is_dom:
            label_result, label_4, label_5 = "WINNER", "RED", "BLUE"
        elif is_missile:
            label_result, label_4, label_5 = "OUTCOME", "FAILED", "T-LEFT"
        else:
            label_result, label_4, label_5 = "RESULT", "FAILED", "CODES"

        for x, label in (
            (COL_DATE, "DATE"), (COL_RESULT, label_result), (COL_TIME, "TIME"),
            (COL_4, label_4), (COL_5, label_5),
        ):
            surf = self.font_hist.render(label, True, COLORS["green"])
            screen.blit(surf, (x, 75))
        pygame.draw.line(screen, COLORS["green"], (40, 100), (SCREEN_WIDTH - 40, 100))

        visible = 12
        # Sort newest-first by timestamp so rows are always in time order,
        # regardless of the order entries were written to the file.
        entries = sorted(
            self.history_data, key=lambda e: e.get("timestamp", ""), reverse=True
        )
        max_scroll = max(0, len(entries) - visible)
        self.history_scroll = min(self.history_scroll, max_scroll)
        page = entries[self.history_scroll:self.history_scroll + visible]

        for i, entry in enumerate(page):
            y = 110 + i * 36
            elapsed = entry.get("elapsed_seconds", 0)
            mins = elapsed // 60
            secs = elapsed % 60
            result = entry.get("result", "?").upper()
            if is_dom:
                result_color = (255, 40, 40) if result == "RED" else (40, 100, 255)
            elif is_missile:
                # Defenders win (green) on abort or timeout; launch is red.
                result_color = COLORS["green"] if result in ("ABORTED", "TIMEOUT") else COLORS["red"]
            else:
                result_color = COLORS["green"] if result == "VICTORY" else COLORS["red"]

            if is_bomb:
                total = entry.get("modules_total", "?")
                solved = entry.get("modules_solved", "?")
                v4 = f"{entry.get('strikes', 0)}/3"
                v5 = f"{solved}/{total}"
            elif is_dom:
                rt = entry.get("red_hold_time", 0)
                bt = entry.get("blue_hold_time", 0)
                v4 = f"{rt // 60}:{rt % 60:02d}"
                v5 = f"{bt // 60}:{bt % 60:02d}"
            elif is_missile:
                tl = entry.get("time_left", 0)
                v4 = str(entry.get("failed_attempts", 0))
                v5 = f"{tl // 60}:{tl % 60:02d}"
            else:
                v4 = str(entry.get("failed_attempts", 0))
                v5 = f"{entry.get('codes_unlocked', 0)}/3"

            for x, text, color in (
                (COL_DATE, str(entry.get("timestamp", "?")), COLORS["white"]),
                (COL_RESULT, result, result_color),
                (COL_TIME, f"{mins}m{secs:02d}s", COLORS["white"]),
                (COL_4, v4, COLORS["white"]),
                (COL_5, v5, COLORS["white"]),
            ):
                screen.blit(self.font_hist.render(text, True, color), (x, y))

        if len(entries) > visible:
            scroll_hint = self.font_desc.render(
                f"Showing {self.history_scroll+1}-{self.history_scroll+len(page)} of {len(entries)}  [UP/DOWN to scroll]",
                True, COLORS["grey"],
            )
            screen.blit(scroll_hint, scroll_hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 60))

        close_hint = self.font_desc.render("Press RED / BACK to close", True, COLORS["grey"])
        screen.blit(close_hint, close_hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 30))
