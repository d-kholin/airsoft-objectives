import pygame
import time
from game_mode import GameMode
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT
from widgets import draw_7seg_time
from ui import draw_menu_item
from presets import timer_presets

TIMER_PRESETS = timer_presets(include_off=True)

MIN_RESPAWNS = 1
MAX_RESPAWNS = 99


class RespawnPoolMode(GameMode):
    name = "Respawn Pool"
    mode_id = "respawn_pool"
    description = "Track a shared pool of respawns for the whole team"

    def setup(self, config=None):
        config = config or {}
        self.font_title = pygame.font.Font(None, 80)
        self.font_big = pygame.font.Font(None, 220)
        self.font_med = pygame.font.Font(None, 52)
        self.font_sm = pygame.font.Font(None, 36)
        self.respawn_selection = 10
        self.timer_selection = 0
        self.custom_minutes = 10
        self.total_respawns = 0
        self.remaining = 0
        self.timer_total = 0
        self.timer_remaining = 0

        if "respawns" in config:
            self._start_play(config["respawns"], config.get("timer", 0))
        else:
            self.phase = "setup_count"

    def handle_input(self, actions):
        if self.phase == "setup_count":
            self._handle_setup_count(actions)
        elif self.phase == "setup_timer":
            self._handle_setup_timer(actions)
        elif self.phase == "setup_custom":
            self._handle_setup_custom(actions)
        elif self.phase == "play":
            self._handle_play(actions)

    def _handle_setup_count(self, actions):
        if "UP" in actions:
            self.respawn_selection = min(MAX_RESPAWNS, self.respawn_selection + 1)
        if "DOWN" in actions:
            self.respawn_selection = max(MIN_RESPAWNS, self.respawn_selection - 1)
        if "START" in actions or "GREEN_BUTTON" in actions:
            self.phase = "setup_timer"

    def _handle_setup_timer(self, actions):
        if "UP" in actions:
            self.timer_selection = (self.timer_selection - 1) % len(TIMER_PRESETS)
        if "DOWN" in actions:
            self.timer_selection = (self.timer_selection + 1) % len(TIMER_PRESETS)
        if "RED_BUTTON" in actions:
            self.phase = "setup_count"
        if "START" in actions or "GREEN_BUTTON" in actions:
            preset = TIMER_PRESETS[self.timer_selection][1]
            if preset is None:
                self.phase = "setup_custom"
            else:
                self._start_play(self.respawn_selection, preset)

    def _handle_setup_custom(self, actions):
        if "UP" in actions:
            self.custom_minutes = min(99, self.custom_minutes + 1)
        if "DOWN" in actions:
            self.custom_minutes = max(1, self.custom_minutes - 1)
        if "RED_BUTTON" in actions:
            self.phase = "setup_timer"
        if "START" in actions or "GREEN_BUTTON" in actions:
            self._start_play(self.respawn_selection, self.custom_minutes * 60)

    def _start_play(self, respawns, timer_seconds):
        self.total_respawns = respawns
        self.remaining = respawns
        self.timer_total = timer_seconds
        self.timer_remaining = timer_seconds
        self.phase = "play"
        self.play_start_time = time.time()

    def _handle_play(self, actions):
        if "GREEN_BUTTON" in actions and self.remaining > 0:
            self.remaining -= 1
            self.app.sound.play("confirm")
        if "RED_BUTTON" in actions and self.remaining < self.total_respawns:
            self.remaining += 1
        if "START" in actions:
            self.remaining = self.total_respawns
            self.timer_remaining = self.timer_total
            self.play_start_time = time.time()

    def update(self, dt):
        if self.phase == "play" and self.timer_total > 0:
            self.timer_remaining = max(0.0, self.timer_remaining - dt)

    def draw(self, screen):
        if self.phase == "setup_count":
            self._draw_setup_count(screen)
        elif self.phase == "setup_timer":
            self._draw_setup_timer(screen)
        elif self.phase == "setup_custom":
            self._draw_setup_custom(screen)
        elif self.phase == "play":
            self._draw_play(screen)

    def _draw_setup_count(self, screen):
        title = self.font_title.render("RESPAWN POOL", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        sub = self.font_sm.render("Set number of respawns", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=110))

        val = self.font_big.render(str(self.respawn_selection), True, COLORS["green"])
        screen.blit(val, val.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))

        hints = self.font_sm.render(
            "UP/DOWN=adjust  START/GREEN=next", True, COLORS["grey"]
        )
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_setup_timer(self, screen):
        title = self.font_title.render("RESPAWN POOL", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        sub = self.font_sm.render("Set an optional timer", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=110))

        col_x = [200, 560]
        row_h = 55
        top = 150
        per_col = (len(TIMER_PRESETS) + 1) // 2
        for i, (label, _secs) in enumerate(TIMER_PRESETS):
            x = col_x[i // per_col]
            y = top + (i % per_col) * row_h
            draw_menu_item(screen, self.font_med, label, i == self.timer_selection, x, y)

        hints = self.font_sm.render(
            "UP/DOWN=select  START/GREEN=confirm  RED=back", True, COLORS["grey"]
        )
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_setup_custom(self, screen):
        title = self.font_title.render("RESPAWN POOL", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        sub = self.font_sm.render("Set custom timer", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=110))

        val = self.font_med.render(f"{self.custom_minutes:02d}:00", True, COLORS["green"])
        screen.blit(val, val.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10)))

        label = self.font_sm.render("MINUTES", True, COLORS["grey"])
        screen.blit(label, label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 50))

        hints = self.font_sm.render(
            "UP/DOWN=adjust  START/GREEN=confirm  RED=back", True, COLORS["grey"]
        )
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_play(self, screen):
        title = self.font_med.render("RESPAWNS REMAINING", True, COLORS["white"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=40))

        color = COLORS["red"] if self.remaining == 0 else COLORS["green"]
        count = self.font_big.render(str(self.remaining), True, color)
        screen.blit(count, count.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))

        of_total = self.font_sm.render(f"of {self.total_respawns}", True, COLORS["grey"])
        screen.blit(of_total, of_total.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 110))

        if self.timer_total > 0:
            timer_color = COLORS["red"] if self.timer_remaining < 30 else COLORS["white"]
            seg_w, seg_h, seg_t, seg_gap = 18, 32, 4, 4
            timer_pixel_w = 6 * (seg_w + seg_gap) + 2 * (seg_t + seg_gap)
            draw_7seg_time(
                screen, SCREEN_WIDTH // 2 - timer_pixel_w // 2, SCREEN_HEIGHT - 110,
                self.timer_remaining, timer_color, seg_w, seg_h, seg_t, seg_gap,
            )

        hints = self.font_sm.render(
            "GREEN=use respawn  RED=return one  START=reset", True, COLORS["grey"]
        )
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

