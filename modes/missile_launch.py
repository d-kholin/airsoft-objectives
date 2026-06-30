import pygame
import math
import random
import time
from game_mode import GameMode
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT, BUTTON_MAP
from ui import draw_menu_item
from widgets import draw_7seg_time, seg7_width, handle_custom_timer, draw_custom_timer
from presets import timer_presets, COUNTDOWN_PRESETS, PHASE_PRESETS
from fonts import get_font

CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

GAME_PRESETS = timer_presets()
LAUNCH_PRESETS = COUNTDOWN_PRESETS

# Phase order and registry keys.
PREP_PHASES = [
    ("FUELING", "fuel_time"),
    ("RAISING", "raise_time"),
    ("ARMING", "arm_time"),
]

PHASE_COMPLETE_TEXT = {
    "FUELING": "FUELING COMPLETE",
    "RAISING": "MISSILE IN LAUNCH POSITION",
    "ARMING": "MISSILE ARMED",
}
PHASE_DEFAULTS = {"fuel_time": 240, "raise_time": 240, "arm_time": 180}

INITIATE_HOLD = 4.0    # seconds to hold BLUE to start a phase
ABORT_HOLD = 15.0      # seconds to hold RED during countdown to abort
SABOTAGE_HOLD = 20.0   # seconds to hold RED during prep to win as attacker
DENIED_FLASH = 1.4

SABOTAGE_FLAVOR = [
    "Unplugging the red wire...",
    "Installing Windows updates...",
    "Ctrl+Alt+Del... Del... Del...",
    "Rebooting in safe mode...",
    "Bypassing the firewall...",
    "Downloading more RAM...",
    "Reformatting C:\\...",
    "Whistling innocently...",
    "Googling 'how to defuse a missile'...",
    "Yanking out the mainframe...",
    "Loosening a suspicious bolt...",
    "Feeding the guidance gyro a virus...",
]

AMBER = (255, 176, 0)
DIM_AMBER = (160, 112, 0)
ALERT_RED = (255, 40, 40)
DIM_RED = (70, 8, 8)


def _telemetry_line():
    templates = [
        lambda: f"GUIDANCE {random.choice(['LOCKED','TRACKING','NOMINAL'])}  AZ {random.randint(0,359):03d}  EL {random.randint(0,89):02d}",
        lambda: f"SILO {random.randint(1,12):02d}  DOOR {random.choice(['OPEN','SEALED'])}  PRESS {random.uniform(0.8,1.2):.2f}ATM",
        lambda: f"FUEL {random.randint(82,100):3d}%  OX {random.randint(82,100):3d}%  THRUST {random.randint(0,100):3d}%",
        lambda: f"TGT {random.choice('ABCDEF')}{random.randint(10,99)}  RANGE {random.randint(1000,9999)}KM  CEP {random.randint(5,80)}m",
        lambda: f"WARHEAD {random.choice(['ARMED','SAFE'])}  SEQ {random.randint(1000,9999)}  CRC {random.choice(['OK','OK','OK','ERR'])}",
        lambda: f"INERTIAL {random.choice(['ALIGNED','SLEWING'])}  GYRO {random.uniform(-0.5,0.5):+.2f}  DRIFT {random.randint(0,9)}",
        lambda: f"UPLINK {random.choice(['SATCOM','HF','VLF'])}  KEY {random.choice(['VALID','VALID','HELD'])}  BIT {random.randint(0,9)}",
    ]
    return random.choice(templates)()


class MissileLaunchMode(GameMode):
    name = "Missile Launch"
    mode_id = "missile_launch"
    description = "Fuel, raise, and arm the missile — then enter launch codes before the enemy stops you"

    def setup(self, config=None):
        config = config or {}
        self.font_big = pygame.font.Font(None, 88)
        self.font_med = pygame.font.Font(None, 50)
        self.font_sm = pygame.font.Font(None, 34)
        self.font_mono = get_font(22, mono=True)
        self.font_label = get_font(26, mono=True)
        self.font_phase = pygame.font.Font(None, 40)

        # Settings
        self.game_total = config.get("game_time", 900)
        self.countdown_total = config.get("countdown", 120)
        self.phase_durations = {
            key: config.get(key, PHASE_DEFAULTS[key])
            for _, key in PREP_PHASES
        }

        # On-box setup state
        self.game_selection = 2
        self.countdown_selection = 1
        self.phase_selections = {key: self._preset_index(key) for _, key in PREP_PHASES}
        self.custom_minutes = 4
        self._setup_phase_key = None   # which phase setting we're editing

        self.game_remaining = 0.0

        # Prep state
        self.prep_index = 0             # 0-2 = current phase, 3 = all done
        self.init_progress = 0.0        # 0..INITIATE_HOLD
        self.phase_remaining = 0.0      # counts down from phase duration
        self.phase_initiated = False

        self.secret_chars = []
        self.secret_index = 0
        self.input_chars = []
        self.input_index = 0
        self.failed_attempts = 0
        self.denied_timer = 0.0

        self.timer_remaining = 0.0
        self.abort_progress = 0.0
        self.sabotage_progress = 0.0

        self.completed_phase_name = ""
        self.show_complete_banner = False
        self.awaiting_release = False

        self.result = None
        self.time_left_at_end = 0
        self.play_start_time = 0

        self.blink = 0.0
        self.anim_time = 0.0
        self.pulse_time = 0.0
        self.launch_anim = 0.0
        self.telemetry = [_telemetry_line() for _ in range(11)]
        self.telemetry_timer = 0.0

        self.action_keys = {}
        for key, action in BUTTON_MAP.items():
            self.action_keys.setdefault(action, []).append(key)

        if any(k in config for _, k in PREP_PHASES) or "game_time" in config:
            code = self.app.config_store.get_launch_code()
            if code:
                self.secret_chars = list(code)
                self._enter_prep()
            else:
                self.phase = "setup_code"
        else:
            self.phase = "setup_game_time"

    def _preset_index(self, key):
        val = self.phase_durations[key]
        for i, (_, v) in enumerate(PHASE_PRESETS):
            if v == val:
                return i
        return 3  # 4 MIN default position

    def _current_phase_name(self):
        if self.prep_index < len(PREP_PHASES):
            return PREP_PHASES[self.prep_index][0]
        return "READY"

    def _current_phase_duration(self):
        if self.prep_index < len(PREP_PHASES):
            return self.phase_durations[PREP_PHASES[self.prep_index][1]]
        return 0

    def _is_held(self, action):
        pressed = pygame.key.get_pressed()
        return any(pressed[k] for k in self.action_keys.get(action, []))

    def _nav(self, selection, count, actions):
        if "UP" in actions:
            selection = (selection - 1) % count
        if "DOWN" in actions:
            selection = (selection + 1) % count
        confirm = "START" in actions or "GREEN_BUTTON" in actions
        return selection, confirm

    def _scroll(self, index, actions):
        if "UP" in actions:
            index = (index - 1) % len(CHARSET)
        if "DOWN" in actions:
            index = (index + 1) % len(CHARSET)
        return index

    # --- input -----------------------------------------------------------

    def handle_input(self, actions):
        handler = {
            "setup_game_time": self._handle_game_time,
            "setup_game_custom": self._handle_game_custom,
            "setup_phase": self._handle_phase_setting,
            "setup_phase_custom": self._handle_phase_custom,
            "setup_countdown": self._handle_countdown,
            "setup_countdown_custom": self._handle_countdown_custom,
            "setup_code": self._handle_setup_code,
            "code_entry": self._handle_code_entry,
        }.get(self.phase)
        if handler:
            handler(actions)
        elif self.phase == "result":
            if "START" in actions or "GREEN_BUTTON" in actions:
                self.setup()

    def _handle_game_time(self, actions):
        self.game_selection, confirm = self._nav(self.game_selection, len(GAME_PRESETS), actions)
        if confirm:
            value = GAME_PRESETS[self.game_selection][1]
            if value is None:
                self.custom_minutes = self.game_total // 60
                self.phase = "setup_game_custom"
            else:
                self.game_total = value
                self._advance_to_phase_setting(0)

    def _handle_game_custom(self, actions):
        self.custom_minutes, result = handle_custom_timer(actions, self.custom_minutes)
        if result == "back":
            self.phase = "setup_game_time"
        elif result == "confirm":
            self.game_total = self.custom_minutes * 60
            self._advance_to_phase_setting(0)

    def _advance_to_phase_setting(self, idx):
        """Move to the setup screen for prep phase `idx`, or to countdown if done."""
        if idx >= len(PREP_PHASES):
            self.phase = "setup_countdown"
            return
        _, key = PREP_PHASES[idx]
        self._setup_phase_key = key
        self._setup_phase_idx = idx
        self.phase = "setup_phase"

    def _handle_phase_setting(self, actions):
        key = self._setup_phase_key
        self.phase_selections[key], confirm = self._nav(
            self.phase_selections[key], len(PHASE_PRESETS), actions)
        if confirm:
            value = PHASE_PRESETS[self.phase_selections[key]][1]
            if value is None:
                self.custom_minutes = self.phase_durations[key] // 60 or 4
                self.phase = "setup_phase_custom"
            else:
                self.phase_durations[key] = value
                self._advance_to_phase_setting(self._setup_phase_idx + 1)

    def _handle_phase_custom(self, actions):
        self.custom_minutes, result = handle_custom_timer(actions, self.custom_minutes)
        key = self._setup_phase_key
        if result == "back":
            self.phase = "setup_phase"
        elif result == "confirm":
            self.phase_durations[key] = self.custom_minutes * 60
            self._advance_to_phase_setting(self._setup_phase_idx + 1)

    def _handle_countdown(self, actions):
        self.countdown_selection, confirm = self._nav(self.countdown_selection, len(LAUNCH_PRESETS), actions)
        if confirm:
            value = LAUNCH_PRESETS[self.countdown_selection][1]
            if value is None:
                self.custom_minutes = self.countdown_total // 60 or 2
                self.phase = "setup_countdown_custom"
            else:
                self.countdown_total = value
                self.phase = "setup_code"

    def _handle_countdown_custom(self, actions):
        self.custom_minutes, result = handle_custom_timer(actions, self.custom_minutes)
        if result == "back":
            self.phase = "setup_countdown"
        elif result == "confirm":
            self.countdown_total = self.custom_minutes * 60
            self.phase = "setup_code"

    def _handle_setup_code(self, actions):
        self.secret_index = self._scroll(self.secret_index, actions)
        if "GREEN_BUTTON" in actions:
            self.secret_chars.append(CHARSET[self.secret_index])
            self.secret_index = 0
            self.app.sound.play("confirm")
        if "RED_BUTTON" in actions and self.secret_chars:
            self.secret_chars.pop()
        if "START" in actions and self.secret_chars:
            self.app.sound.play("confirm")
            self._enter_prep()

    def _handle_code_entry(self, actions):
        self.input_index = self._scroll(self.input_index, actions)
        if "GREEN_BUTTON" in actions:
            self.input_chars.append(CHARSET[self.input_index])
            self.input_index = 0
            self.app.sound.play("confirm")
        if "RED_BUTTON" in actions and self.input_chars:
            self.input_chars.pop()
        if "START" in actions and self.input_chars:
            if "".join(self.input_chars) == "".join(self.secret_chars):
                self._begin_countdown()
            else:
                self.failed_attempts += 1
                self.denied_timer = DENIED_FLASH
                self.input_chars = []
                self.input_index = 0
                self.app.sound.play("error")

    def _enter_prep(self):
        self.phase = "prep"
        self.prep_index = 0
        self.init_progress = 0.0
        self.phase_initiated = False
        self.phase_remaining = float(self._current_phase_duration())
        self.game_remaining = float(self.game_total)
        self.play_start_time = time.time()

    def _begin_countdown(self):
        self.phase = "countdown"
        self.timer_remaining = float(self.countdown_total)
        self.abort_progress = 0.0
        self.app.sound.play("confirm")

    # --- update ----------------------------------------------------------

    def update(self, dt):
        self.blink += dt
        self.anim_time += dt
        if self.denied_timer > 0:
            self.denied_timer = max(0.0, self.denied_timer - dt)

        self.telemetry_timer += dt
        if self.telemetry_timer > 0.35:
            self.telemetry_timer = 0.0
            self.telemetry.pop(0)
            self.telemetry.append(_telemetry_line())

        if self.phase in ("prep", "code_entry"):
            self.game_remaining -= dt
            if self.game_remaining <= 0:
                self.game_remaining = 0
                self._finish("TIMEOUT")
                return

        if self.phase == "prep":
            self._update_prep(dt)

        elif self.phase == "countdown":
            self.timer_remaining -= dt
            if self._is_held("RED_BUTTON"):
                self.abort_progress += dt
                if self.abort_progress >= ABORT_HOLD:
                    self._finish("ABORTED")
                    return
            else:
                self.abort_progress = 0.0
            if self.timer_remaining <= 0:
                self.timer_remaining = 0
                self._finish("LAUNCHED")

        elif self.phase == "result":
            self.pulse_time += dt
            if self.result == "LAUNCHED":
                self.launch_anim += dt

    def _update_prep(self, dt):
        blue = self._is_held("BLUE_BUTTON")
        red = self._is_held("RED_BUTTON")
        dur = float(self._current_phase_duration())

        if red:
            self.sabotage_progress += dt
            if self.sabotage_progress >= SABOTAGE_HOLD:
                self._finish("SABOTAGED")
                return
        else:
            self.sabotage_progress = 0.0

        if self.awaiting_release:
            if not blue:
                self.awaiting_release = False
            return

        if not self.phase_initiated:
            if blue and not red:
                self.init_progress += dt
                self.show_complete_banner = False
                if self.init_progress >= INITIATE_HOLD:
                    self.phase_initiated = True
                    self.phase_remaining = dur
                    self.init_progress = INITIATE_HOLD
                    self.app.sound.play("confirm")
            else:
                self.init_progress = 0.0
        else:
            if not red:
                self.phase_remaining -= dt
                if self.phase_remaining <= 0:
                    self.phase_remaining = 0
                    self._complete_phase()

    def _complete_phase(self):
        self.completed_phase_name = PREP_PHASES[self.prep_index][0]
        self.prep_index += 1
        self.app.sound.play("confirm")
        if self.prep_index >= len(PREP_PHASES):
            self.phase = "code_entry"
            self.input_chars = []
            self.input_index = 0
        else:
            self.phase_initiated = False
            self.init_progress = 0.0
            self.phase_remaining = float(self._current_phase_duration())
            self.show_complete_banner = True
            self.awaiting_release = True

    def _finish(self, result):
        self.result = result
        self.time_left_at_end = max(0, int(self.game_remaining))
        self.phase = "result"
        self.pulse_time = 0.0
        self.launch_anim = 0.0
        self._save_history()
        if result in ("LAUNCHED", "SABOTAGED"):
            self.app.sound.play("victory")
        else:
            self.app.sound.play("defeat")

    # --- drawing ---------------------------------------------------------

    def draw(self, screen):
        if self.phase == "setup_game_time":
            self._draw_choice(screen, "Set game time", GAME_PRESETS, self.game_selection)
        elif self.phase == "setup_game_custom":
            draw_custom_timer(screen, self.font_big, self.font_sm, "MISSILE LAUNCH",
                              self.custom_minutes, sub="Set custom game time (minutes)")
        elif self.phase == "setup_phase":
            name = PREP_PHASES[self._setup_phase_idx][0]
            self._draw_choice(screen, f"Set {name} duration",
                              PHASE_PRESETS, self.phase_selections[self._setup_phase_key])
        elif self.phase == "setup_phase_custom":
            name = PREP_PHASES[self._setup_phase_idx][0]
            draw_custom_timer(screen, self.font_big, self.font_sm, "MISSILE LAUNCH",
                              self.custom_minutes, sub=f"Set custom {name} duration")
        elif self.phase == "setup_countdown":
            self._draw_choice(screen, "Set launch countdown", LAUNCH_PRESETS, self.countdown_selection)
        elif self.phase == "setup_countdown_custom":
            draw_custom_timer(screen, self.font_big, self.font_sm, "MISSILE LAUNCH",
                              self.custom_minutes, sub="Set custom countdown")
        elif self.phase == "setup_code":
            self._draw_setup_code(screen)
        elif self.phase == "prep":
            self._draw_prep(screen)
        elif self.phase == "code_entry":
            self._draw_code_entry(screen)
        elif self.phase == "countdown":
            self._draw_countdown(screen)
        elif self.phase == "result":
            self._draw_result(screen)

    def _draw_grid(self, screen, color):
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(screen, color, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))

    def _draw_char_entry(self, screen, chars, index, x, y, accent):
        cx = x
        char_h = self.font_med.get_height()
        if chars:
            confirmed = self.font_med.render("".join(chars), True, accent)
            screen.blit(confirmed, (cx, y))
            cx += confirmed.get_width() + 6
        box = pygame.Rect(cx, y, 34, char_h)
        pygame.draw.rect(screen, accent, box)
        curr = self.font_med.render(CHARSET[index], True, COLORS["bg"])
        screen.blit(curr, curr.get_rect(center=box.center))
        prev = self.font_sm.render(CHARSET[(index - 1) % len(CHARSET)], True, COLORS["grey"])
        screen.blit(prev, prev.get_rect(centerx=box.centerx, bottom=box.top - 4))
        nxt = self.font_sm.render(CHARSET[(index + 1) % len(CHARSET)], True, COLORS["grey"])
        screen.blit(nxt, nxt.get_rect(centerx=box.centerx, top=box.bottom + 4))

    def _draw_telemetry(self, screen, rect, color):
        screen.set_clip(rect)
        for i, line in enumerate(self.telemetry):
            c = color if i % 2 == 0 else tuple(max(0, v - 30) for v in color)
            surf = self.font_mono.render(line, True, c)
            screen.blit(surf, (rect.x, rect.y + i * 22))
        screen.set_clip(None)

    def _draw_choice(self, screen, sub, presets, selection):
        self._draw_grid(screen, (16, 12, 0))
        title = self.font_big.render("MISSILE LAUNCH", True, AMBER)
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=24))
        sub_surf = self.font_sm.render(sub, True, COLORS["white"])
        screen.blit(sub_surf, sub_surf.get_rect(centerx=SCREEN_WIDTH // 2, y=118))

        # Two-column layout for long preset lists.
        per_col = (len(presets) + 1) // 2
        col_x = [160, 560]
        row_h = min(52, max(32, (SCREEN_HEIGHT - 200) // per_col))
        for i, (label, _) in enumerate(presets):
            x = col_x[i // per_col]
            y = 160 + (i % per_col) * row_h
            draw_menu_item(screen, self.font_phase, label, i == selection,
                           x, y, accent=AMBER)
        hints = self.font_sm.render("UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 38))

    def _fmt(self, secs):
        return f"{int(secs) // 60}:{int(secs) % 60:02d}"

    def _draw_setup_code(self, screen):
        self._draw_grid(screen, (16, 12, 0))
        title = self.font_med.render("LAUNCH AUTHORIZATION", True, AMBER)
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=36))
        sub = self.font_sm.render(
            "GAME MASTER: set the secret launch code", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=98))
        label = self.font_label.render("LAUNCH CODE:", True, AMBER)
        screen.blit(label, (120, 220))
        self._draw_char_entry(screen, self.secret_chars, self.secret_index, 130, 270, AMBER)

        durations = "   ".join(
            f"{name} {self._fmt(self.phase_durations[key])}"
            for name, key in PREP_PHASES)
        cfg = self.font_sm.render(
            f"Game {self._fmt(self.game_total)}   {durations}   "
            f"Countdown {self._fmt(self.countdown_total)}",
            True, COLORS["grey"])
        screen.blit(cfg, cfg.get_rect(centerx=SCREEN_WIDTH // 2, y=400))

        hints = self.font_sm.render(
            "UP/DOWN=char  GREEN=add  RED=delete  START=arm system", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 38))

    def _draw_missile(self, screen, cx, base_y, scale, flame, raised_pct=0.0):
        """Wireframe missile schematic."""
        offset = int(raised_pct * 60 * scale)
        base_y -= offset
        bw = int(26 * scale)
        bh = int(120 * scale)
        nose = int(40 * scale)
        lw = max(1, int(1.5 * scale))
        color = AMBER
        dim = DIM_AMBER

        body = pygame.Rect(cx - bw // 2, base_y - bh, bw, bh)
        tip = (cx, base_y - bh - nose)
        # Body outline
        pygame.draw.rect(screen, color, body, lw)
        # Nose cone outline
        pygame.draw.polygon(screen, color, [
            (body.left, base_y - bh), (body.right, base_y - bh), tip], lw)
        # Section lines
        for frac in (0.25, 0.55, 0.75):
            sy = body.top + int(bh * frac)
            pygame.draw.line(screen, dim, (body.left, sy), (body.right, sy), 1)
        # Center line
        pygame.draw.line(screen, dim, (cx, tip[1]), (cx, base_y), 1)
        # Fin outlines
        fin = int(22 * scale)
        pygame.draw.polygon(screen, color, [
            (body.left, base_y - fin), (body.left - fin, base_y), (body.left, base_y)], lw)
        pygame.draw.polygon(screen, color, [
            (body.right, base_y - fin), (body.right + fin, base_y), (body.right, base_y)], lw)
        # Nozzle
        nw = int(bw * 0.6)
        pygame.draw.line(screen, color, (cx - nw // 2, base_y), (cx + nw // 2, base_y), lw)
        pygame.draw.line(screen, color, (cx - nw // 2, base_y), (cx - nw // 3, base_y + int(8 * scale)), lw)
        pygame.draw.line(screen, color, (cx + nw // 2, base_y), (cx + nw // 3, base_y + int(8 * scale)), lw)
        # Annotation lines
        ax = body.right + int(12 * scale)
        for i, (label, frac) in enumerate([("NOSE", 0.0), ("GUIDANCE", 0.3), ("PAYLOAD", 0.6), ("ENGINE", 0.9)]):
            ay = body.top + int(bh * frac)
            pygame.draw.line(screen, dim, (body.right, ay), (ax, ay), 1)
            surf = self.font_mono.render(label, True, dim)
            screen.blit(surf, (ax + 4, ay - surf.get_height() // 2))
        # Exhaust plume (wireframe flicker)
        if flame > 0:
            for j in range(3):
                flick = random.uniform(0.5, 1.0)
                fl = int(50 * scale * flame * flick)
                fw = int(bw * (0.5 - j * 0.12))
                col = AMBER if j == 0 else ALERT_RED if j == 1 else dim
                pygame.draw.line(screen, col, (cx - fw, base_y + j * 3), (cx, base_y + fl), 1)
                pygame.draw.line(screen, col, (cx + fw, base_y + j * 3), (cx, base_y + fl), 1)

    def _draw_phase_checklist(self, screen, y):
        """Small status indicators for each phase — no progress bars here."""
        cx = SCREEN_WIDTH // 2
        phase_w = 180
        gap = 20
        total = len(PREP_PHASES) * phase_w + (len(PREP_PHASES) - 1) * gap
        sx = cx - total // 2

        for i, (name, _) in enumerate(PREP_PHASES):
            x = sx + i * (phase_w + gap)
            h = 28
            if i < self.prep_index or (i <= self.prep_index and self.phase == "code_entry"):
                pygame.draw.rect(screen, COLORS["green"], (x, y, phase_w, h), border_radius=3)
                label = self.font_phase.render(f"[OK] {name}", True, COLORS["bg"])
            elif i == self.prep_index:
                pygame.draw.rect(screen, AMBER, (x, y, phase_w, h), 2, border_radius=3)
                label = self.font_phase.render(name, True, AMBER)
            else:
                pygame.draw.rect(screen, COLORS["grey"], (x, y, phase_w, h), 1, border_radius=3)
                label = self.font_phase.render(name, True, COLORS["grey"])
            screen.blit(label, label.get_rect(center=(x + phase_w // 2, y + h // 2)))

    def _draw_active_phase_bar(self, screen, y):
        """Full-width progress bar + status text for the current prep phase."""
        name = self._current_phase_name()
        dur = float(self._current_phase_duration())
        bar_x, bar_w, bar_h = 60, SCREEN_WIDTH - 120, 32

        if self.init_progress <= 0 and not self.phase_initiated:
            pct = 0.0
            status = f"READY — HOLD [BLUE] TO BEGIN {name}"
            bar_col = COLORS["grey"]
        elif not self.phase_initiated:
            pct = self.init_progress / INITIATE_HOLD
            status = f"INITIATING {name}..."
            bar_col = COLORS["yellow"]
        else:
            pct = 1.0 - (self.phase_remaining / dur) if dur > 0 else 1.0
            status = f"{name}  {self._fmt(self.phase_remaining)}"
            bar_col = AMBER

        # Status text above the bar
        label = self.font_med.render(status, True, bar_col)
        screen.blit(label, label.get_rect(centerx=SCREEN_WIDTH // 2, y=y))

        # Full-width bar below the text
        bar_y = y + label.get_height() + 8
        pygame.draw.rect(screen, (30, 30, 40), (bar_x, bar_y, bar_w, bar_h))
        fill = int(bar_w * pct)
        if fill > 0:
            pygame.draw.rect(screen, bar_col, (bar_x, bar_y, fill, bar_h))
        pygame.draw.rect(screen, bar_col, (bar_x, bar_y, bar_w, bar_h), 2)

    def _draw_prep(self, screen):
        self._draw_grid(screen, (16, 12, 0))
        pygame.draw.rect(screen, DIM_AMBER, (0, 0, SCREEN_WIDTH, 52))
        header = self.font_sm.render("STRATEGIC LAUNCH CONTROL  //  PREP SEQUENCE", True, AMBER)
        screen.blit(header, header.get_rect(centerx=SCREEN_WIDTH // 2, centery=26))

        # Game clock
        clock_col = ALERT_RED if self.game_remaining < 60 else AMBER
        clock = self.font_med.render(self._fmt(self.game_remaining), True, clock_col)
        screen.blit(clock, clock.get_rect(right=SCREEN_WIDTH - 16, y=62))
        gl = self.font_sm.render("GAME TIME", True, COLORS["grey"])
        screen.blit(gl, gl.get_rect(right=SCREEN_WIDTH - 16, y=104))

        # Phase checklist (compact, no overlaid progress)
        self._draw_phase_checklist(screen, 72)

        # Active phase: status text + full-width bar below
        self._draw_active_phase_bar(screen, 130)

        # Missile wireframe
        raised = 0.0
        if self.prep_index > 1 or (self.prep_index == 1 and self.phase_initiated):
            dur = float(self.phase_durations["raise_time"])
            if self.prep_index > 1:
                raised = 1.0
            elif dur > 0:
                raised = 1.0 - (self.phase_remaining / dur)
        fuel_flame = 0.0
        if self.prep_index > 0 or (self.prep_index == 0 and self.phase_initiated):
            fuel_flame = 0.15 + 0.1 * math.sin(self.anim_time * 6)
        self._draw_missile(screen, 130, 480, 1.0, flame=fuel_flame, raised_pct=raised)

        # Telemetry
        self._draw_telemetry(screen, pygame.Rect(560, 260, 460, 220), DIM_AMBER)

        # Phase-complete banner (pulses until player starts next phase)
        if self.show_complete_banner:
            self._draw_complete_banner(screen)

        # Sabotage overlay
        if self.sabotage_progress > 0:
            self._draw_sabotage_overlay(screen)

        # Controls
        if self.sabotage_progress > 0:
            hint_text = "RELEASE [RED] TO CANCEL"
            hint_col = ALERT_RED
        elif not self.phase_initiated:
            hint_text = "HOLD [BLUE] 4s to initiate   //   Release resets"
            hint_col = COLORS["grey"]
        else:
            hint_text = "Timer runs automatically   //   [RED] = SABOTAGE"
            hint_col = COLORS["grey"]
        hint = self.font_sm.render(hint_text, True, hint_col)
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 28))

    def _draw_complete_banner(self, screen):
        """Pulsing green banner in the lower portion — overlays the prep screen."""
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 6)
        alpha = int(60 + 140 * pulse)

        banner_h = 100
        banner_y = SCREEN_HEIGHT - 140
        banner = pygame.Surface((SCREEN_WIDTH, banner_h), pygame.SRCALPHA)
        banner.fill((0, 40, 20, alpha))
        # Scanlines
        for sy in range(4, banner_h, 4):
            pygame.draw.line(banner, (0, 60, 30, min(255, alpha)), (0, sy), (SCREEN_WIDTH, sy), 1)
        screen.blit(banner, (0, banner_y))

        g = int(120 + 135 * pulse)
        col = (0, g, int(g * 0.4))
        pygame.draw.line(screen, col, (0, banner_y), (SCREEN_WIDTH, banner_y), 2)
        pygame.draw.line(screen, col, (0, banner_y + banner_h), (SCREEN_WIDTH, banner_y + banner_h), 2)

        title = self.font_med.render(
            PHASE_COMPLETE_TEXT.get(self.completed_phase_name, f"{self.completed_phase_name} COMPLETE"),
            True, col)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, banner_y + 30)))

        next_name = PREP_PHASES[self.prep_index][0]
        sub = self.font_sm.render(
            f">>> HOLD [BLUE] TO BEGIN {next_name} >>>", True, col)
        screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, banner_y + 70)))

    def _draw_sabotage_overlay(self, screen):
        """Flashing red sabotage-in-progress banner."""
        pct = self.sabotage_progress / SABOTAGE_HOLD
        flash = int(self.blink * 6) % 2 == 0

        banner_h = 110
        banner_y = SCREEN_HEIGHT - 172
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 10)
        alpha = int(80 + 140 * pulse)
        banner = pygame.Surface((SCREEN_WIDTH, banner_h), pygame.SRCALPHA)
        banner.fill((60, 0, 0, alpha))
        for sy in range(4, banner_h, 4):
            pygame.draw.line(banner, (120, 0, 0, min(255, alpha)), (0, sy), (SCREEN_WIDTH, sy), 1)
        screen.blit(banner, (0, banner_y))

        edge_col = ALERT_RED if flash else (120, 20, 20)
        pygame.draw.line(screen, edge_col, (0, banner_y), (SCREEN_WIDTH, banner_y), 2)
        pygame.draw.line(screen, edge_col, (0, banner_y + banner_h), (SCREEN_WIDTH, banner_y + banner_h), 2)

        title_col = ALERT_RED if flash else (180, 30, 30)
        title = self.font_med.render("!!! SABOTAGE IN PROGRESS !!!", True, title_col)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, banner_y + 28)))

        # Progress bar
        bar_w, bar_h = 560, 24
        bx = SCREEN_WIDTH // 2 - bar_w // 2
        by = banner_y + 56
        pygame.draw.rect(screen, (40, 0, 0), (bx, by, bar_w, bar_h))
        pygame.draw.rect(screen, ALERT_RED, (bx, by, int(bar_w * pct), bar_h))
        pygame.draw.rect(screen, ALERT_RED, (bx, by, bar_w, bar_h), 2)

        secs_left = max(0, int(SABOTAGE_HOLD - self.sabotage_progress) + 1)
        flavor = SABOTAGE_FLAVOR[int(self.sabotage_progress // 2) % len(SABOTAGE_FLAVOR)]
        sub = self.font_sm.render(
            f"{flavor}  ({secs_left}s)", True, COLORS["grey"])
        screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, banner_y + banner_h + 18)))

    def _draw_code_entry(self, screen):
        self._draw_grid(screen, (16, 12, 0))
        pygame.draw.rect(screen, DIM_AMBER, (0, 0, SCREEN_WIDTH, 52))
        header = self.font_sm.render("STRATEGIC LAUNCH CONTROL  //  READY", True, AMBER)
        screen.blit(header, header.get_rect(centerx=SCREEN_WIDTH // 2, centery=26))

        clock_col = ALERT_RED if self.game_remaining < 60 else AMBER
        clock = self.font_med.render(self._fmt(self.game_remaining), True, clock_col)
        screen.blit(clock, clock.get_rect(right=SCREEN_WIDTH - 16, y=62))
        gl = self.font_sm.render("GAME TIME", True, COLORS["grey"])
        screen.blit(gl, gl.get_rect(right=SCREEN_WIDTH - 16, y=104))

        self._draw_phase_checklist(screen, 72)

        ready = self.font_med.render("MISSILE READY — ENTER LAUNCH CODE", True, COLORS["green"])
        screen.blit(ready, ready.get_rect(centerx=SCREEN_WIDTH // 2, y=210))

        label = self.font_label.render("AUTH CODE:", True, AMBER)
        screen.blit(label, (120, 290))
        self._draw_char_entry(screen, self.input_chars, self.input_index, 130, 340, COLORS["green"])

        if self.denied_timer > 0 and int(self.denied_timer * 6) % 2 == 0:
            denied = self.font_med.render("ACCESS DENIED", True, ALERT_RED)
            screen.blit(denied, denied.get_rect(centerx=SCREEN_WIDTH // 2, y=430))
        elif int(self.blink * 2) % 2 == 0:
            wait = self.font_sm.render("> AWAITING INPUT_", True, COLORS["green"])
            screen.blit(wait, (130, 440))

        if self.failed_attempts:
            fa = self.font_sm.render(f"FAILED ATTEMPTS: {self.failed_attempts}", True, COLORS["grey"])
            screen.blit(fa, (130, 490))

        hint = self.font_sm.render(
            "UP/DOWN=char  GREEN=add  RED=delete  START=transmit", True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 38))

    def _draw_countdown(self, screen):
        alert = int(self.blink * 3) % 2 == 0
        self._draw_grid(screen, DIM_RED)

        banner_col = ALERT_RED if alert else (120, 20, 20)
        pygame.draw.rect(screen, (25, 0, 0), (0, 0, SCREEN_WIDTH, 56))
        banner = self.font_med.render("///  LAUNCH SEQUENCE INITIATED  ///", True, banner_col)
        screen.blit(banner, banner.get_rect(centerx=SCREEN_WIDTH // 2, centery=28))

        seg_w, seg_h, seg_t, seg_gap = 46, 84, 8, 8
        total_w = seg7_width(seg_w, seg_t, seg_gap)
        cx = SCREEN_WIDTH // 2 - total_w // 2
        seg_col = ALERT_RED if self.timer_remaining >= 10 or alert else AMBER
        draw_7seg_time(screen, cx, 92, self.timer_remaining, seg_col,
                       seg_w, seg_h, seg_t, seg_gap)
        tmin = self.font_sm.render("T-MINUS TO LAUNCH", True, COLORS["grey"])
        screen.blit(tmin, tmin.get_rect(centerx=SCREEN_WIDTH // 2, y=196))

        self._draw_missile(screen, 120, 470, 1.0,
                           flame=0.35 + 0.2 * math.sin(self.anim_time * 12),
                           raised_pct=1.0)
        self._draw_telemetry(screen, pygame.Rect(620, 226, 400, 200), DIM_AMBER)

        if self.abort_progress > 0:
            pct = self.abort_progress / ABORT_HOLD
            lbl = self.font_med.render(
                f"ABORT SEQUENCE {int(pct * 100)}%  ({int(self.abort_progress)}/{int(ABORT_HOLD)}s)",
                True, COLORS["green"])
            screen.blit(lbl, lbl.get_rect(centerx=SCREEN_WIDTH // 2, y=462))
            bar_w, bar_h = 560, 30
            bx = SCREEN_WIDTH // 2 - bar_w // 2
            by = 512
            pygame.draw.rect(screen, (10, 40, 20), (bx, by, bar_w, bar_h))
            pygame.draw.rect(screen, COLORS["green"], (bx, by, int(bar_w * pct), bar_h))
            pygame.draw.rect(screen, COLORS["green"], (bx, by, bar_w, bar_h), 2)
        else:
            prompt_col = COLORS["green"] if alert else (0, 110, 45)
            prompt = self.font_med.render(
                f"HOLD  [RED]  {int(ABORT_HOLD)}s  TO ABORT", True, prompt_col)
            screen.blit(prompt, prompt.get_rect(centerx=SCREEN_WIDTH // 2, y=496))

        hint = self.font_sm.render(
            "Attackers: reach the box and hold RED to cancel the launch",
            True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 28))

    def _draw_result(self, screen):
        if self.result == "LAUNCHED":
            self._draw_grid(screen, DIM_RED)
            rise = min(self.launch_anim * 220, SCREEN_HEIGHT + 200)
            base_y = SCREEN_HEIGHT + 40 - rise
            self._draw_missile(screen, SCREEN_WIDTH // 2, int(base_y), 1.4,
                               flame=1.0, raised_pct=1.0)
            if self.launch_anim < 0.4:
                flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                flash.fill(AMBER)
                flash.set_alpha(int(220 * (1 - self.launch_anim / 0.4)))
                screen.blit(flash, (0, 0))
            alpha = int((math.sin(self.pulse_time * 5) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in COLORS["green"])
            text = self.font_big.render("MISSILE LAUNCHED", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 120)))
            sub_text = "TARGET DESTROYED"
        elif self.result == "SABOTAGED":
            self._draw_grid(screen, DIM_RED)
            alpha = int((math.sin(self.pulse_time * 6) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in ALERT_RED)
            text = self.font_big.render("SABOTAGE COMPLETE", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
            sub_text = "ATTACKERS WIN"
        elif self.result == "ABORTED":
            self._draw_grid(screen, DIM_RED)
            alpha = int((math.sin(self.pulse_time * 4) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in ALERT_RED)
            text = self.font_big.render("LAUNCH ABORTED", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
            sub_text = "THREAT NEUTRALIZED"
        else:
            self._draw_grid(screen, (0, 30, 12))
            alpha = int((math.sin(self.pulse_time * 4) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in ALERT_RED)
            text = self.font_big.render("TIME EXPIRED", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
            sub_text = "LAUNCH PREVENTED"

        sub_surf = self.font_med.render(sub_text, True, col)
        sub_y = 190 if self.result == "LAUNCHED" else SCREEN_HEIGHT // 2
        screen.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_WIDTH // 2, sub_y)))

        phases_done = min(self.prep_index, len(PREP_PHASES))
        if self.result == "LAUNCHED":
            stat = f"Countdown: {self._fmt(self.countdown_total)}"
        elif self.result == "SABOTAGED":
            stat = f"Sabotaged after {phases_done}/{len(PREP_PHASES)} phases"
        elif self.result == "ABORTED":
            stat = f"Aborted with {self._fmt(self.time_left_at_end)} on countdown"
        else:
            stat = f"Phases: {phases_done}/{len(PREP_PHASES)}"
        stats = self.font_sm.render(
            f"{stat}  |  Failed codes: {self.failed_attempts}", True, COLORS["white"])
        screen.blit(stats, stats.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70)))

        prompt = self.font_sm.render("Press START to play again", True, COLORS["grey"])
        screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)))

    def _save_history(self):
        elapsed = time.time() - self.play_start_time if self.play_start_time else 0
        self.save_history({
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "result": self.result,
            "elapsed_seconds": round(elapsed),
            "failed_attempts": self.failed_attempts,
            "game_time": self.game_total,
            "countdown_total": self.countdown_total,
            "phases_completed": min(self.prep_index, len(PREP_PHASES)),
            "time_left": self.time_left_at_end,
        })
