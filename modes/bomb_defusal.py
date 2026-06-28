import pygame
import math
import random
import json
import time
from pathlib import Path
from game_mode import GameMode, GameState
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT

HISTORY_FILE = Path(__file__).parent.parent / "data" / "bomb_defusal_history.json"

TIMER_PRESETS = [
    ("3 MIN", 180),
    ("5 MIN", 300),
    ("7 MIN", 420),
    ("10 MIN", 600),
    ("15 MIN", 900),
]

MODULE_PRESETS = [
    ("3 MODULES", 3),
    ("4 MODULES", 4),
    ("5 MODULES", 5),
    ("6 MODULES", 6),
]

WIRE_COLORS = ["RED", "BLUE", "YELLOW", "WHITE", "BLACK"]
WIRE_RGB = {
    "RED": (255, 40, 40),
    "BLUE": (40, 100, 255),
    "YELLOW": (255, 220, 0),
    "WHITE": (240, 240, 240),
    "BLACK": (60, 60, 60),
}

KEYPAD_COLUMNS = [
    ["BOLT", "STAR", "DROP", "GEAR", "KNOT", "RING", "DART"],
    ["MOON", "BOLT", "RING", "WAVE", "STAR", "COIL", "FANG"],
    ["GEAR", "WAVE", "KNOT", "DART", "MOON", "DROP", "APEX"],
    ["STAR", "KNOT", "FANG", "RING", "GEAR", "APEX", "COIL"],
    ["DART", "MOON", "COIL", "APEX", "DROP", "FANG", "BOLT"],
    ["COIL", "GEAR", "MOON", "FANG", "BOLT", "WAVE", "KNOT"],
]

BUTTON_COLORS = ["RED", "BLUE", "YELLOW", "WHITE"]
BUTTON_LABELS = ["ABORT", "DETONATE", "HOLD", "PRESS", "DISARM"]

DIM_GREEN = (0, 90, 35)
DIM_RED = (90, 0, 0)


def _generate_serial():
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    return (
        random.choice(letters)
        + random.choice(letters)
        + random.choice(digits)
        + random.choice(digits)
        + random.choice(digits)
        + random.choice(digits)
    )


def _serial_last_odd(serial):
    return int(serial[-1]) % 2 == 1


def _serial_has_vowel(serial):
    return any(c in "AEIOU" for c in serial)


def _generate_wires_module():
    count = random.randint(3, 6)
    wires = [random.choice(WIRE_COLORS) for _ in range(count)]
    return {"type": "wires", "wires": wires, "solved": False, "selected": 0}


def _solve_wires(module, serial):
    wires = module["wires"]
    n = len(wires)
    if n == 3:
        if "RED" not in wires:
            return 1
        elif wires[-1] == "WHITE":
            return n - 1
        else:
            return 0
    elif n == 4:
        red_count = wires.count("RED")
        if red_count > 1 and _serial_last_odd(serial):
            for i in range(n - 1, -1, -1):
                if wires[i] == "RED":
                    return i
        elif wires[-1] == "YELLOW" and red_count == 0:
            return 0
        elif wires.count("BLUE") == 1:
            return 0
        else:
            return 1
    elif n == 5:
        if wires[-1] == "BLACK" and _serial_last_odd(serial):
            return 3
        elif wires.count("RED") == 1 and wires.count("YELLOW") > 1:
            return 0
        elif "BLACK" not in wires:
            return 1
        else:
            return 0
    else:
        if "YELLOW" not in wires and _serial_last_odd(serial):
            return 2
        elif wires.count("YELLOW") == 1 and wires.count("WHITE") > 1:
            return 3
        elif "RED" not in wires:
            return n - 1
        else:
            return 3


def _generate_keypad_module():
    col_idx = random.randint(0, len(KEYPAD_COLUMNS) - 1)
    column = KEYPAD_COLUMNS[col_idx]
    symbols = random.sample(column, 4)
    correct_order = sorted(symbols, key=lambda s: column.index(s))
    return {
        "type": "keypad",
        "symbols": symbols,
        "correct_order": correct_order,
        "pressed": [],
        "solved": False,
        "selected": 0,
    }


def _generate_button_module():
    color = random.choice(BUTTON_COLORS)
    label = random.choice(BUTTON_LABELS)
    return {
        "type": "button",
        "color": color,
        "label": label,
        "solved": False,
        "phase": "waiting",
        "held": False,
        "release_digit": None,
    }


def _solve_button_action(module, serial):
    color = module["color"]
    label = module["label"]
    if color == "BLUE" and label == "ABORT":
        return "hold"
    if label == "DETONATE":
        return "press"
    if color == "WHITE" and _serial_has_vowel(serial):
        return "hold"
    if color == "RED" and label == "HOLD":
        return "press"
    return "hold"


def _solve_button_release(module):
    color = module["color"]
    if color == "BLUE":
        return 4
    if color == "YELLOW":
        return 5
    return 1


class BombDefusalMode(GameMode):
    name = "Bomb Defusal"
    description = "Defuse the bomb with help from your team over radio"

    def setup(self, config=None):
        self.font_big = pygame.font.Font(None, 72)
        self.font_med = pygame.font.Font(None, 48)
        self.font_sm = pygame.font.Font(None, 36)
        self.font_mono = pygame.font.Font(None, 28)
        self.phase = "setup_timer"
        self.timer_selection = 1
        self.module_selection = 0
        self.setup_step = "timer"
        self.timer_total = 0
        self.timer_remaining = 0
        self.num_modules = 3
        self.serial = ""
        self.modules = []
        self.current_module = 0
        self.strikes = 0
        self.max_strikes = 3
        self.result = None
        self.pulse_time = 0.0
        self.play_start_time = 0
        self.failed_attempts = 0
        self.state = GameState.RUNNING

    def handle_input(self, actions):
        if self.phase == "setup_timer":
            self._handle_setup_timer(actions)
        elif self.phase == "setup_modules":
            self._handle_setup_modules(actions)
        elif self.phase == "play":
            self._handle_play(actions)
        elif self.phase == "result":
            if "START" in actions or "GREEN_BUTTON" in actions:
                self.setup()

    def _handle_setup_timer(self, actions):
        if "UP" in actions:
            self.timer_selection = (self.timer_selection - 1) % len(TIMER_PRESETS)
        if "DOWN" in actions:
            self.timer_selection = (self.timer_selection + 1) % len(TIMER_PRESETS)
        if "START" in actions or "GREEN_BUTTON" in actions:
            self.timer_total = TIMER_PRESETS[self.timer_selection][1]
            self.timer_remaining = self.timer_total
            self.phase = "setup_modules"

    def _handle_setup_modules(self, actions):
        if "UP" in actions:
            self.module_selection = (self.module_selection - 1) % len(MODULE_PRESETS)
        if "DOWN" in actions:
            self.module_selection = (self.module_selection + 1) % len(MODULE_PRESETS)
        if "START" in actions or "GREEN_BUTTON" in actions:
            self.num_modules = MODULE_PRESETS[self.module_selection][1]
            self._generate_bomb()
            self.phase = "play"
            self.play_start_time = time.time()

    def _generate_bomb(self):
        self.serial = _generate_serial()
        self.modules = []
        generators = [_generate_wires_module, _generate_keypad_module, _generate_button_module]
        for _ in range(self.num_modules):
            gen = random.choice(generators)
            self.modules.append(gen())
        self.current_module = 0

    def _handle_play(self, actions):
        if "RED_BUTTON" in actions:
            self.current_module = (self.current_module - 1) % len(self.modules)
        if "BLUE_BUTTON" in actions:
            self.current_module = (self.current_module + 1) % len(self.modules)

        mod = self.modules[self.current_module]
        if mod["solved"]:
            return

        if mod["type"] == "wires":
            self._handle_wires(mod, actions)
        elif mod["type"] == "keypad":
            self._handle_keypad(mod, actions)
        elif mod["type"] == "button":
            self._handle_button(mod, actions)

    def _handle_wires(self, mod, actions):
        if "UP" in actions:
            mod["selected"] = (mod["selected"] - 1) % len(mod["wires"])
        if "DOWN" in actions:
            mod["selected"] = (mod["selected"] + 1) % len(mod["wires"])
        if "GREEN_BUTTON" in actions or "START" in actions:
            correct = _solve_wires(mod, self.serial)
            if mod["selected"] == correct:
                mod["solved"] = True
                self.app.sound.play("confirm")
                self._check_win()
            else:
                self._strike()

    def _handle_keypad(self, mod, actions):
        if "UP" in actions:
            mod["selected"] = (mod["selected"] - 1) % len(mod["symbols"])
        if "DOWN" in actions:
            mod["selected"] = (mod["selected"] + 1) % len(mod["symbols"])
        if "GREEN_BUTTON" in actions or "START" in actions:
            sym = mod["symbols"][mod["selected"]]
            if sym in mod["pressed"]:
                return
            expected = mod["correct_order"][len(mod["pressed"])]
            if sym == expected:
                mod["pressed"].append(sym)
                self.app.sound.play("confirm")
                if len(mod["pressed"]) == len(mod["symbols"]):
                    mod["solved"] = True
                    self._check_win()
            else:
                mod["pressed"] = []
                self._strike()

    def _handle_button(self, mod, actions):
        action = _solve_button_action(mod, self.serial)
        if action == "press":
            if "GREEN_BUTTON" in actions or "START" in actions:
                if not mod["held"]:
                    mod["solved"] = True
                    self.app.sound.play("confirm")
                    self._check_win()
                else:
                    self._strike()
                    mod["held"] = False
                    mod["phase"] = "waiting"
        else:
            if "GREEN_BUTTON" in actions and not mod["held"]:
                mod["held"] = True
                mod["phase"] = "holding"
                mod["release_digit"] = _solve_button_release(mod)
            if "START" in actions and mod["held"]:
                timer_ones = int(self.timer_remaining) % 10
                if timer_ones == mod["release_digit"]:
                    mod["solved"] = True
                    mod["phase"] = "waiting"
                    self.app.sound.play("confirm")
                    self._check_win()
                else:
                    mod["held"] = False
                    mod["phase"] = "waiting"
                    self._strike()

    def _strike(self):
        self.strikes += 1
        self.failed_attempts += 1
        self.app.sound.play("error")
        if self.strikes >= self.max_strikes:
            self.result = "defeat"
            self.phase = "result"
            self.pulse_time = 0.0
            self._save_history()
            self.app.sound.play("defeat")

    def _check_win(self):
        if all(m["solved"] for m in self.modules):
            self.result = "victory"
            self.phase = "result"
            self.pulse_time = 0.0
            self._save_history()
            self.app.sound.play("victory")

    def update(self, dt):
        if self.phase == "play":
            self.timer_remaining -= dt
            if self.timer_remaining <= 0:
                self.timer_remaining = 0
                self.result = "defeat"
                self.phase = "result"
                self.pulse_time = 0.0
                self._save_history()
                self.app.sound.play("defeat")
        if self.phase == "result":
            self.pulse_time += dt

    def draw(self, screen):
        if self.phase == "setup_timer":
            self._draw_setup_timer(screen)
        elif self.phase == "setup_modules":
            self._draw_setup_modules(screen)
        elif self.phase == "play":
            self._draw_play(screen)
        elif self.phase == "result":
            self._draw_result(screen)

    def _draw_setup_timer(self, screen):
        title = self.font_big.render("BOMB DEFUSAL SETUP", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        sub = self.font_sm.render("Set countdown timer", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=90))

        for i, (label, _) in enumerate(TIMER_PRESETS):
            selected = i == self.timer_selection
            color = COLORS["green"] if selected else COLORS["grey"]
            prefix = "> " if selected else "  "
            surf = self.font_med.render(f"{prefix}{label}", True, color)
            screen.blit(surf, (SCREEN_WIDTH // 2 - 100, 140 + i * 50))

        hints = self.font_sm.render("UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_setup_modules(self, screen):
        title = self.font_big.render("BOMB DEFUSAL SETUP", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        sub = self.font_sm.render("Set number of modules", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=90))

        for i, (label, _) in enumerate(MODULE_PRESETS):
            selected = i == self.module_selection
            color = COLORS["green"] if selected else COLORS["grey"]
            prefix = "> " if selected else "  "
            surf = self.font_med.render(f"{prefix}{label}", True, color)
            screen.blit(surf, (SCREEN_WIDTH // 2 - 120, 140 + i * 50))

        hints = self.font_sm.render("UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_play(self, screen):
        # Header
        pygame.draw.rect(screen, DIM_RED, (0, 0, SCREEN_WIDTH, 50))
        title = self.font_med.render("BOMB ACTIVE", True, COLORS["red"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, centery=25))

        # Timer
        mins = int(self.timer_remaining) // 60
        secs = int(self.timer_remaining) % 60
        timer_color = COLORS["red"] if self.timer_remaining < 30 else COLORS["white"]
        timer_surf = self.font_med.render(f"{mins:02d}:{secs:02d}", True, timer_color)
        screen.blit(timer_surf, timer_surf.get_rect(right=SCREEN_WIDTH - 15, centery=25))

        # Strikes
        strike_text = "X " * self.strikes + "O " * (self.max_strikes - self.strikes)
        strike_surf = self.font_sm.render(f"STRIKES: {strike_text}", True, COLORS["red"])
        screen.blit(strike_surf, (15, 12))

        # Serial number
        serial_surf = self.font_sm.render(f"S/N: {self.serial}", True, COLORS["white"])
        screen.blit(serial_surf, serial_surf.get_rect(right=SCREEN_WIDTH - 15, y=55))

        # Module tabs
        pygame.draw.line(screen, DIM_RED, (0, 80), (SCREEN_WIDTH, 80))
        tab_y = 85
        tab_x = 15
        for i, mod in enumerate(self.modules):
            is_current = i == self.current_module
            if mod["solved"]:
                color = COLORS["green"]
                label = f"[{i+1}] OK"
            elif is_current:
                color = COLORS["yellow"]
                label = f"[{i+1}] {mod['type'].upper()}"
            else:
                color = COLORS["grey"]
                label = f"[{i+1}] {mod['type'].upper()}"
            surf = self.font_sm.render(label, True, color)
            screen.blit(surf, (tab_x, tab_y))
            tab_x += surf.get_width() + 20

        pygame.draw.line(screen, DIM_RED, (0, 115), (SCREEN_WIDTH, 115))

        # Current module content
        mod = self.modules[self.current_module]
        if mod["solved"]:
            solved_surf = self.font_big.render("MODULE DISARMED", True, COLORS["green"])
            screen.blit(solved_surf, solved_surf.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        elif mod["type"] == "wires":
            self._draw_wires_module(screen, mod)
        elif mod["type"] == "keypad":
            self._draw_keypad_module(screen, mod)
        elif mod["type"] == "button":
            self._draw_button_module(screen, mod)

        # Navigation hint
        nav = self.font_mono.render(
            "RED/BLUE=switch module   UP/DOWN=navigate   GREEN=act",
            True, COLORS["grey"],
        )
        screen.blit(nav, nav.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 25))

    def _draw_wires_module(self, screen, mod):
        header = self.font_med.render("WIRES", True, COLORS["white"])
        screen.blit(header, (40, 130))

        info = self.font_sm.render(
            f"{len(mod['wires'])} wires — select and cut the correct one",
            True, COLORS["grey"],
        )
        screen.blit(info, (40, 170))

        for i, color_name in enumerate(mod["wires"]):
            y = 220 + i * 50
            is_selected = i == mod["selected"]

            if is_selected:
                pygame.draw.rect(screen, (40, 40, 50), (35, y - 5, SCREEN_WIDTH - 70, 45))

            wire_color = WIRE_RGB[color_name]
            pygame.draw.rect(screen, wire_color, (80, y + 8, 400, 12))
            pygame.draw.rect(screen, wire_color, (60, y, 20, 28), border_radius=4)
            pygame.draw.rect(screen, wire_color, (480, y, 20, 28), border_radius=4)

            label = self.font_sm.render(f"{i+1}. {color_name}", True, COLORS["white"] if is_selected else COLORS["grey"])
            screen.blit(label, (520, y + 2))

            if is_selected:
                cursor = self.font_sm.render(">", True, COLORS["yellow"])
                screen.blit(cursor, (45, y + 2))

    def _draw_keypad_module(self, screen, mod):
        header = self.font_med.render("KEYPAD", True, COLORS["white"])
        screen.blit(header, (40, 130))

        info = self.font_sm.render("Press symbols in the correct order", True, COLORS["grey"])
        screen.blit(info, (40, 170))

        for i, sym in enumerate(mod["symbols"]):
            y = 220 + i * 60
            is_selected = i == mod["selected"]
            already_pressed = sym in mod["pressed"]

            if is_selected:
                pygame.draw.rect(screen, (40, 40, 50), (35, y - 5, 300, 50))

            if already_pressed:
                color = COLORS["green"]
                prefix = "[OK] "
            elif is_selected:
                color = COLORS["yellow"]
                prefix = ">  "
            else:
                color = COLORS["grey"]
                prefix = "   "

            surf = self.font_med.render(f"{prefix}{sym}", True, color)
            screen.blit(surf, (50, y))

        pressed_count = len(mod["pressed"])
        progress = self.font_sm.render(f"Progress: {pressed_count}/{len(mod['symbols'])}", True, COLORS["white"])
        screen.blit(progress, (500, 220))

        if mod["pressed"]:
            order_text = " > ".join(mod["pressed"])
            order_surf = self.font_mono.render(f"Order: {order_text}", True, COLORS["green"])
            screen.blit(order_surf, (500, 260))

    def _draw_button_module(self, screen, mod):
        header = self.font_med.render("THE BUTTON", True, COLORS["white"])
        screen.blit(header, (40, 130))

        btn_color = WIRE_RGB.get(mod["color"], COLORS["white"])
        btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, 200, 240, 120)
        pygame.draw.rect(screen, btn_color, btn_rect, border_radius=12)
        pygame.draw.rect(screen, COLORS["white"], btn_rect, 3, border_radius=12)

        label_color = COLORS["bg"] if mod["color"] in ("WHITE", "YELLOW") else COLORS["white"]
        label = self.font_med.render(mod["label"], True, label_color)
        screen.blit(label, label.get_rect(center=btn_rect.center))

        color_label = self.font_sm.render(f"Color: {mod['color']}", True, COLORS["white"])
        screen.blit(color_label, color_label.get_rect(centerx=SCREEN_WIDTH // 2, y=340))

        if mod["held"]:
            strip_color = WIRE_RGB.get(mod["color"], COLORS["white"])
            pygame.draw.rect(screen, strip_color, (SCREEN_WIDTH // 2 - 60, 380, 120, 20))
            hold_info = self.font_sm.render(
                "HOLDING — press START to release", True, COLORS["yellow"]
            )
            screen.blit(hold_info, hold_info.get_rect(centerx=SCREEN_WIDTH // 2, y=410))
            hint = self.font_mono.render(
                "Check manual for when to release based on strip color",
                True, COLORS["grey"],
            )
            screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=445))
        else:
            action_hint = self.font_sm.render(
                "GREEN = tap the button  |  hold GREEN then START = hold & release",
                True, COLORS["grey"],
            )
            screen.blit(action_hint, action_hint.get_rect(centerx=SCREEN_WIDTH // 2, y=400))

    def _draw_result(self, screen):
        alpha = int((math.sin(self.pulse_time * 4) + 1) * 127)

        if self.result == "victory":
            text = "BOMB DEFUSED"
            sub = f"Time remaining: {int(self.timer_remaining) // 60}m{int(self.timer_remaining) % 60:02d}s"
            base_color = COLORS["green"]
        else:
            if self.strikes >= self.max_strikes:
                text = "BOOM!"
                sub = "Too many strikes"
            else:
                text = "BOOM!"
                sub = "Time ran out"
            base_color = COLORS["red"]

        color = tuple(min(255, max(40, int(c * alpha / 255))) for c in base_color)
        surf = self.font_big.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))

        sub_surf = self.font_med.render(sub, True, color)
        screen.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)))

        elapsed = time.time() - self.play_start_time
        stats = self.font_sm.render(
            f"Strikes: {self.strikes}  |  Time: {int(elapsed) // 60}m{int(elapsed) % 60:02d}s",
            True, COLORS["white"],
        )
        screen.blit(stats, stats.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60)))

        prompt = self.font_sm.render("Press START to play again", True, COLORS["grey"])
        screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100)))

    def _save_history(self):
        elapsed = time.time() - self.play_start_time
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "result": self.result,
            "elapsed_seconds": round(elapsed),
            "strikes": self.strikes,
            "modules_total": len(self.modules),
            "modules_solved": sum(1 for m in self.modules if m["solved"]),
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
