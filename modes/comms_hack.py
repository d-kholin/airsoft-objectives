import pygame
import math
import random
import json
import time
from pathlib import Path
from game_mode import GameMode, GameState
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT
from ui import draw_menu_item

HISTORY_FILE = Path(__file__).parent.parent / "data" / "comms_hack_history.json"

CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
TIMER_PRESETS = [
    ("OFF", 0),
    ("3 MIN", 180),
    ("5 MIN", 300),
    ("10 MIN", 600),
    ("15 MIN", 900),
    ("20 MIN", 1200),
]

DIM_GREEN = (0, 90, 35)
AMBER = (200, 160, 0)
DIM_AMBER = (80, 60, 0)


def _random_stat_line():
    templates = [
        lambda: f"PKT TX: {random.randint(1000,99999):>6}  RX: {random.randint(1000,99999):>6}  LOSS: {random.uniform(0,5):.1f}%",
        lambda: f"FREQ {random.uniform(30,900):.3f} MHz  PWR {random.randint(-80,-20)} dBm  SNR {random.randint(5,40)} dB",
        lambda: f"NODE {random.choice('ABCDEF')}{random.randint(1,9)}{random.randint(0,9)}  LATENCY {random.randint(2,200)}ms  STATUS {'ONLINE' if random.random()>0.2 else 'TIMEOUT'}",
        lambda: f"UPLINK {random.randint(100,9999)} kbps  DOWNLINK {random.randint(100,9999)} kbps  JITTER {random.randint(1,50)}ms",
        lambda: f"SECTOR {random.randint(1,16):02d}  ENCRYPT AES-{random.choice(['128','256'])}  HANDSHAKE {'OK' if random.random()>0.1 else 'RETRY'}",
        lambda: f"RELAY {random.choice(['ALPHA','BRAVO','CHARLIE','DELTA','ECHO'])}-{random.randint(1,9)}  HOP {random.randint(1,8)}  TTL {random.randint(10,255)}",
        lambda: f"BUFFER {random.randint(10,100)}%  QUEUE {random.randint(0,500)}  DROPPED {random.randint(0,50)}",
        lambda: f"SCAN {random.randint(1,360)}DEG  CONTACTS {random.randint(0,12)}  BEARING {random.randint(0,359):03d}",
    ]
    return random.choice(templates)()


class CommsHackMode(GameMode):
    name = "Comms Array Hack"
    description = "Enter 3 codes to hack the comms array before time runs out"

    def setup(self, config=None):
        self.font_big = pygame.font.Font(None, 72)
        self.font_med = pygame.font.Font(None, 48)
        self.font_sm = pygame.font.Font(None, 36)
        self.font_mono = pygame.font.Font(None, 28)
        self.phase = "setup_codes"
        self.codes = []
        self.current_code = []
        self.char_index = 0
        self.timer_selection = 0
        self.timer_total = 0
        self.timer_remaining = 0
        self.matched = [False, False, False]
        self.input_chars = []
        self.input_char_index = 0
        self.result = None
        self.pulse_time = 0.0
        self.decrypt_attempt = ""
        self.decrypt_timer = 0.0
        self.decrypt_duration = 3.0
        self.stat_lines = [_random_stat_line() for _ in range(12)]
        self.stat_scroll_timer = 0.0
        self.cursor_blink = 0.0
        self.cmd_log = []
        self.state = GameState.RUNNING

    def handle_input(self, actions):
        if self.phase == "setup_codes":
            self._handle_setup_codes(actions)
        elif self.phase == "setup_timer":
            self._handle_setup_timer(actions)
        elif self.phase == "play":
            self._handle_play(actions)
        elif self.phase == "result":
            if "START" in actions or "GREEN_BUTTON" in actions:
                self.setup()

    def _handle_setup_codes(self, actions):
        if "UP" in actions:
            self.char_index = (self.char_index - 1) % len(CHARSET)
        if "DOWN" in actions:
            self.char_index = (self.char_index + 1) % len(CHARSET)
        if "GREEN_BUTTON" in actions:
            self.current_code.append(CHARSET[self.char_index])
            self.char_index = 0
            self.app.sound.play("confirm")
        if "RED_BUTTON" in actions and self.current_code:
            self.current_code.pop()
        if "START" in actions and self.current_code:
            self.codes.append("".join(self.current_code))
            self.current_code = []
            self.char_index = 0
            self.app.sound.play("confirm")
            if len(self.codes) == 3:
                self.phase = "setup_timer"

    def _handle_setup_timer(self, actions):
        if "UP" in actions:
            self.timer_selection = (self.timer_selection - 1) % len(TIMER_PRESETS)
        if "DOWN" in actions:
            self.timer_selection = (self.timer_selection + 1) % len(TIMER_PRESETS)
        if "START" in actions or "GREEN_BUTTON" in actions:
            self.timer_total = TIMER_PRESETS[self.timer_selection][1]
            self.timer_remaining = self.timer_total
            self.input_chars = []
            self.input_char_index = 0
            self.phase = "play"
            self.play_start_time = time.time()
            self.failed_attempts = 0
            self.app.sound.play("confirm")

    def _handle_play(self, actions):
        if "UP" in actions:
            self.input_char_index = (self.input_char_index - 1) % len(CHARSET)
        if "DOWN" in actions:
            self.input_char_index = (self.input_char_index + 1) % len(CHARSET)
        if "GREEN_BUTTON" in actions:
            self.input_chars.append(CHARSET[self.input_char_index])
            self.input_char_index = 0
            self.app.sound.play("confirm")
        if "RED_BUTTON" in actions and self.input_chars:
            self.input_chars.pop()
        if "START" in actions and self.input_chars:
            self.decrypt_attempt = "".join(self.input_chars)
            self.input_chars = []
            self.input_char_index = 0
            self.decrypt_timer = 0.0
            self.decrypt_duration = 3.0
            self.phase = "decrypting"
            self.cmd_log.append(f"DECRYPT {self.decrypt_attempt} ...")
            if len(self.cmd_log) > 4:
                self.cmd_log = self.cmd_log[-4:]

    def update(self, dt):
        if self.phase in ("play", "decrypting"):
            self.cursor_blink += dt
            self.stat_scroll_timer += dt
            if self.stat_scroll_timer > 0.4:
                self.stat_scroll_timer = 0.0
                self.stat_lines.pop(0)
                self.stat_lines.append(_random_stat_line())
            if self.timer_total > 0:
                self.timer_remaining -= dt
                if self.timer_remaining <= 0:
                    self.timer_remaining = 0
                    self.result = "defeat"
                    self.phase = "result"
                    self.pulse_time = 0.0
                    self._save_history()
                    self.app.sound.play("defeat")
        if self.phase == "decrypting":
            self.decrypt_timer += dt
            if self.decrypt_timer >= self.decrypt_duration:
                matched_any = False
                for i, code in enumerate(self.codes):
                    if not self.matched[i] and self.decrypt_attempt == code:
                        self.matched[i] = True
                        matched_any = True
                        self.cmd_log.append(f"  >> ACCESS GRANTED [{i+1}/3]")
                        self.app.sound.play("confirm")
                        break
                if not matched_any:
                    self.failed_attempts += 1
                    self.cmd_log.append(f"  >> ACCESS DENIED")
                    self.app.sound.play("error")
                if len(self.cmd_log) > 4:
                    self.cmd_log = self.cmd_log[-4:]
                if all(self.matched):
                    self.result = "victory"
                    self.phase = "result"
                    self.pulse_time = 0.0
                    self._save_history()
                    self.app.sound.play("victory")
                else:
                    self.phase = "play"
        if self.phase == "result":
            self.pulse_time += dt
            self.stat_scroll_timer += dt
            if self.stat_scroll_timer > 0.4:
                self.stat_scroll_timer = 0.0
                if self.stat_lines:
                    self.stat_lines.pop(0)
                    self.stat_lines.append(_random_stat_line())

    def draw(self, screen):
        if self.phase == "setup_codes":
            self._draw_setup_codes(screen)
        elif self.phase == "setup_timer":
            self._draw_setup_timer(screen)
        elif self.phase == "play":
            self._draw_play(screen)
        elif self.phase == "decrypting":
            self._draw_play(screen)
            self._draw_decrypt_overlay(screen)
        elif self.phase == "result":
            self._draw_result(screen)

    def _draw_setup_codes(self, screen):
        title = self.font_big.render("GAME MASTER SETUP", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=15))

        info = self.font_sm.render(
            f"Enter code {len(self.codes) + 1} of 3", True, COLORS["white"]
        )
        screen.blit(info, info.get_rect(centerx=SCREEN_WIDTH // 2, y=85))

        for i, code in enumerate(self.codes):
            surf = self.font_sm.render(
                f"Code {i + 1}: {code}", True, COLORS["green"]
            )
            screen.blit(surf, (60, 130 + i * 35))

        self._draw_char_input(screen, self.current_code, self.char_index, 60, 250)

        hints = self.font_sm.render(
            "UP/DOWN=scroll  GREEN=add char  RED=delete  START=confirm code",
            True, COLORS["grey"],
        )
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_setup_timer(self, screen):
        title = self.font_big.render("SET TIMER", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        for i, (label, _secs) in enumerate(TIMER_PRESETS):
            draw_menu_item(
                screen, self.font_med, label,
                i == self.timer_selection, SCREEN_WIDTH // 2 - 100, 120 + i * 50,
            )

        hints = self.font_sm.render(
            "UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"]
        )
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_play(self, screen):
        # --- Header bar ---
        pygame.draw.rect(screen, DIM_GREEN, (0, 0, SCREEN_WIDTH, 50))
        title = self.font_med.render("CENTRAL COMMS UNIT", True, COLORS["green"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, centery=25))

        if self.timer_total > 0:
            mins = int(self.timer_remaining) // 60
            secs = int(self.timer_remaining) % 60
            timer_color = COLORS["red"] if self.timer_remaining < 30 else COLORS["green"]
            timer_surf = self.font_sm.render(f"{mins:02d}:{secs:02d}", True, timer_color)
            screen.blit(timer_surf, timer_surf.get_rect(right=SCREEN_WIDTH - 15, centery=25))

        # --- Lock status ---
        locked_count = sum(1 for m in self.matched if not m)
        if locked_count > 0:
            status_text = f"STATUS: LOCKED [{3-locked_count}/3 UNLOCKED]"
            status_color = COLORS["red"]
        else:
            status_text = "STATUS: ALL LOCKS UNLOCKED"
            status_color = COLORS["green"]
        status_surf = self.font_sm.render(status_text, True, status_color)
        screen.blit(status_surf, (15, 58))

        # --- Separator ---
        pygame.draw.line(screen, DIM_GREEN, (0, 80), (SCREEN_WIDTH, 80))

        # --- Scrolling stats panel (left side) ---
        stats_rect = pygame.Rect(10, 85, 480, 280)
        for i, line in enumerate(self.stat_lines):
            color = DIM_GREEN if i % 2 == 0 else (0, 70, 30)
            surf = self.font_mono.render(line, True, color)
            screen.blit(surf, (stats_rect.x, stats_rect.y + i * 23))

        # --- Auth slots (right side) ---
        slots_x = 510
        slot_label = self.font_sm.render("AUTH SLOTS", True, COLORS["green"])
        screen.blit(slot_label, (slots_x, 88))
        pygame.draw.line(screen, DIM_GREEN, (slots_x, 115), (SCREEN_WIDTH - 10, 115))

        for i in range(3):
            y = 125 + i * 45
            if self.matched[i]:
                indicator = self.font_sm.render(f"[{i+1}] UNLOCKED", True, COLORS["green"])
            else:
                indicator = self.font_sm.render(f"[{i+1}] LOCKED", True, COLORS["red"])
            screen.blit(indicator, (slots_x, y))

        # --- Separator ---
        pygame.draw.line(screen, DIM_GREEN, (0, 370), (SCREEN_WIDTH, 370))

        # --- Command log ---
        log_y = 378
        for entry in self.cmd_log:
            color = COLORS["green"] if "GRANTED" in entry else COLORS["red"]
            surf = self.font_mono.render(f"  {entry}", True, color)
            screen.blit(surf, (10, log_y))
            log_y += 22

        # --- Command line input ---
        cmd_y = SCREEN_HEIGHT - 42
        pygame.draw.line(screen, DIM_GREEN, (0, cmd_y - 5), (SCREEN_WIDTH, cmd_y - 5))

        prefix = self.font_sm.render("root@comms:~# AUTH ", True, COLORS["green"])
        screen.blit(prefix, (10, cmd_y))
        self._draw_char_input(screen, self.input_chars, self.input_char_index, 10 + prefix.get_width(), cmd_y - 6)

    def _save_history(self):
        elapsed = time.time() - self.play_start_time
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "result": self.result,
            "elapsed_seconds": round(elapsed),
            "failed_attempts": self.failed_attempts,
            "codes_unlocked": sum(self.matched),
            "timer_preset": self.timer_total,
        }
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if HISTORY_FILE.exists():
            try:
                history = json.loads(HISTORY_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        history.append(entry)
        HISTORY_FILE.write_text(json.dumps(history, indent=2))

    @staticmethod
    def load_history():
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _draw_char_input(self, screen, chars, char_index, x, y):
        cx = x
        char_h = self.font_med.get_height()
        if chars:
            confirmed = self.font_med.render("".join(chars), True, COLORS["green"])
            screen.blit(confirmed, (cx, y))
            cx += confirmed.get_width() + 4

        prev_char = CHARSET[(char_index - 1) % len(CHARSET)]
        curr_char = CHARSET[char_index]
        next_char = CHARSET[(char_index + 1) % len(CHARSET)]

        selector_bg = pygame.Rect(cx, y, 30, char_h)
        pygame.draw.rect(screen, COLORS["yellow"], selector_bg)
        curr_surf = self.font_med.render(curr_char, True, COLORS["bg"])
        screen.blit(curr_surf, curr_surf.get_rect(center=selector_bg.center))

        prev_surf = self.font_sm.render(prev_char, True, COLORS["grey"])
        screen.blit(prev_surf, prev_surf.get_rect(centerx=selector_bg.centerx, bottom=selector_bg.top - 4))

        next_surf = self.font_sm.render(next_char, True, COLORS["grey"])
        screen.blit(next_surf, next_surf.get_rect(centerx=selector_bg.centerx, top=selector_bg.bottom + 4))

    def _draw_decrypt_overlay(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        progress = min(self.decrypt_timer / self.decrypt_duration, 1.0)
        pct = int(progress * 100)

        label = self.font_med.render(f"DECRYPTING... {pct}%", True, COLORS["green"])
        screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))

        bar_w, bar_h = 500, 30
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = SCREEN_HEIGHT // 2
        pygame.draw.rect(screen, DIM_GREEN, (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            pygame.draw.rect(screen, COLORS["green"], (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(screen, COLORS["green"], (bar_x, bar_y, bar_w, bar_h), 2)

        blocks = "#" * int(progress * 20) + "-" * (20 - int(progress * 20))
        block_surf = self.font_sm.render(f"[{blocks}]", True, COLORS["green"])
        screen.blit(block_surf, block_surf.get_rect(center=(SCREEN_WIDTH // 2, bar_y + bar_h + 25)))

    def _draw_result(self, screen):
        for i, line in enumerate(self.stat_lines):
            color = (0, 30, 15)
            surf = self.font_mono.render(line, True, color)
            screen.blit(surf, (10, 20 + i * 23))

        alpha = int((math.sin(self.pulse_time * 4) + 1) * 127)

        if self.result == "victory":
            text = "SYSTEM COMPROMISED"
            sub = "ALL LOCKS UNLOCKED"
            base_color = COLORS["green"]
        else:
            text = "CONNECTION LOST"
            sub = "MISSION FAILED"
            base_color = COLORS["red"]

        color = tuple(min(255, max(40, int(c * alpha / 255))) for c in base_color)
        surf = self.font_big.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))

        sub_surf = self.font_med.render(sub, True, color)
        screen.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)))

        prompt = self.font_sm.render("Press START to play again", True, COLORS["grey"])
        screen.blit(
            prompt,
            prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70)),
        )
