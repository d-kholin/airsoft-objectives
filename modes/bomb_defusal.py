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

MORSE_WORDS = {
    "SHELL": 3.505,
    "HALLS": 3.515,
    "SLICK": 3.522,
    "TRICK": 3.532,
    "BOXES": 3.535,
    "LEAKS": 3.542,
    "STROBE": 3.545,
    "BISTRO": 3.552,
    "FLICK": 3.555,
    "BOMBS": 3.565,
    "BREAK": 3.572,
    "BRICK": 3.575,
    "STEAK": 3.582,
    "STING": 3.592,
    "VECTOR": 3.595,
    "BEATS": 3.600,
}

MORSE_CODE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
}

SIMON_COLORS = ["RED", "BLUE", "GREEN", "YELLOW"]
SIMON_RGB = {
    "RED": (255, 40, 40),
    "BLUE": (40, 100, 255),
    "GREEN": (0, 200, 80),
    "YELLOW": (255, 220, 0),
}
SIMON_DIM_RGB = {
    "RED": (80, 15, 15),
    "BLUE": (15, 35, 80),
    "GREEN": (0, 60, 25),
    "YELLOW": (80, 70, 0),
}

SIMON_MAP_NO_VOWEL = {
    0: {"RED": "BLUE", "BLUE": "RED", "GREEN": "YELLOW", "YELLOW": "GREEN"},
    1: {"RED": "YELLOW", "BLUE": "GREEN", "GREEN": "BLUE", "YELLOW": "RED"},
    2: {"RED": "GREEN", "BLUE": "YELLOW", "GREEN": "RED", "YELLOW": "BLUE"},
}
SIMON_MAP_VOWEL = {
    0: {"RED": "BLUE", "BLUE": "YELLOW", "GREEN": "GREEN", "YELLOW": "RED"},
    1: {"RED": "GREEN", "BLUE": "BLUE", "GREEN": "RED", "YELLOW": "YELLOW"},
    2: {"RED": "YELLOW", "BLUE": "RED", "GREEN": "BLUE", "YELLOW": "GREEN"},
}

NUMPAD_INDICATORS = ["SIG", "FRK", "CAR", "IND", "MSA", "BOB"]

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


def _generate_morse_module():
    word = random.choice(list(MORSE_WORDS.keys()))
    freq = MORSE_WORDS[word]
    morse = "  ".join(MORSE_CODE[c] for c in word)
    return {
        "type": "morse",
        "word": word,
        "morse": morse,
        "frequency": freq,
        "solved": False,
        "selected_freq": 3.500,
        "flash_timer": 0.0,
    }


def _generate_simon_module():
    length = random.randint(3, 5)
    sequence = [random.choice(SIMON_COLORS) for _ in range(length)]
    return {
        "type": "simon",
        "sequence": sequence,
        "stage": 1,
        "solved": False,
        "input": [],
        "flash_index": 0,
        "flash_timer": 0.0,
        "phase": "showing",
        "show_count": 0,
        "pause_timer": 0.0,
    }


def _solve_simon(sequence, stage, strikes, serial_has_vowel):
    mapping = SIMON_MAP_VOWEL if serial_has_vowel else SIMON_MAP_NO_VOWEL
    strike_key = min(strikes, 2)
    chart = mapping[strike_key]
    return [chart[c] for c in sequence[:stage]]


def _generate_numpad_module():
    lit_indicators = random.sample(NUMPAD_INDICATORS, random.randint(1, 3))
    digit_count = random.randint(1, 3)
    display_num = random.randint(1, 4)
    return {
        "type": "numpad",
        "indicators": {ind: (ind in lit_indicators) for ind in NUMPAD_INDICATORS},
        "lit_indicators": lit_indicators,
        "display_number": display_num,
        "solved": False,
        "selected": 0,
        "options": _numpad_options(display_num),
    }


def _numpad_options(display_num):
    base = [1, 2, 3, 4]
    random.shuffle(base)
    return base


def _solve_numpad(module, serial):
    display = module["display_number"]
    lit = module["lit_indicators"]
    has_frk = "FRK" in lit
    has_car = "CAR" in lit
    has_sig = "SIG" in lit
    last_odd = _serial_last_odd(serial)

    if display == 1:
        if has_frk and last_odd:
            return 3
        elif has_car:
            return 4
        else:
            return 2
    elif display == 2:
        if has_sig and has_frk:
            return 4
        elif last_odd:
            return 1
        else:
            return 3
    elif display == 3:
        if has_car and not last_odd:
            return 1
        elif has_sig:
            return 2
        else:
            return 4
    else:
        if has_frk and has_car:
            return 2
        elif has_sig and last_odd:
            return 3
        else:
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
        self.play_end_time = 0
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
        generators = [
            _generate_wires_module, _generate_keypad_module, _generate_button_module,
            _generate_morse_module, _generate_simon_module, _generate_numpad_module,
        ]
        random.shuffle(generators)
        self.modules = [gen() for gen in generators[:self.num_modules]]
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
        elif mod["type"] == "morse":
            self._handle_morse(mod, actions)
        elif mod["type"] == "simon":
            self._handle_simon(mod, actions)
        elif mod["type"] == "numpad":
            self._handle_numpad(mod, actions)

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

    def _handle_morse(self, mod, actions):
        if "UP" in actions:
            mod["selected_freq"] = round(mod["selected_freq"] + 0.005, 3)
            if mod["selected_freq"] > 3.600:
                mod["selected_freq"] = 3.500
        if "DOWN" in actions:
            mod["selected_freq"] = round(mod["selected_freq"] - 0.005, 3)
            if mod["selected_freq"] < 3.500:
                mod["selected_freq"] = 3.600
        if "GREEN_BUTTON" in actions or "START" in actions:
            if abs(mod["selected_freq"] - mod["frequency"]) < 0.001:
                mod["solved"] = True
                self.app.sound.play("confirm")
                self._check_win()
            else:
                self._strike()

    def _handle_simon(self, mod, actions):
        if mod["phase"] == "showing":
            return
        color_map = {"UP": "RED", "DOWN": "GREEN", "GREEN_BUTTON": "YELLOW", "START": "BLUE"}
        for action, color in color_map.items():
            if action in actions:
                expected = _solve_simon(
                    mod["sequence"], mod["stage"], self.strikes,
                    _serial_has_vowel(self.serial),
                )
                idx = len(mod["input"])
                if color == expected[idx]:
                    mod["input"].append(color)
                    self.app.sound.play("confirm")
                    if len(mod["input"]) == len(expected):
                        if mod["stage"] >= len(mod["sequence"]):
                            mod["solved"] = True
                            self._check_win()
                        else:
                            mod["stage"] += 1
                            mod["input"] = []
                            mod["phase"] = "showing"
                            mod["flash_index"] = 0
                            mod["flash_timer"] = 0.0
                            mod["show_count"] = 0
                            mod["pause_timer"] = 1.0
                else:
                    mod["input"] = []
                    mod["phase"] = "showing"
                    mod["flash_index"] = 0
                    mod["flash_timer"] = 0.0
                    mod["show_count"] = 0
                    mod["pause_timer"] = 1.0
                    self._strike()
                break

    def _handle_numpad(self, mod, actions):
        if "UP" in actions:
            mod["selected"] = (mod["selected"] - 1) % len(mod["options"])
        if "DOWN" in actions:
            mod["selected"] = (mod["selected"] + 1) % len(mod["options"])
        if "GREEN_BUTTON" in actions or "START" in actions:
            chosen = mod["options"][mod["selected"]]
            correct = _solve_numpad(mod, self.serial)
            if chosen == correct:
                mod["solved"] = True
                self.app.sound.play("confirm")
                self._check_win()
            else:
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
            for mod in self.modules:
                if mod["solved"]:
                    continue
                if mod["type"] == "morse":
                    mod["flash_timer"] += dt
                if mod["type"] == "simon" and mod["phase"] == "showing":
                    if mod["pause_timer"] > 0:
                        mod["pause_timer"] -= dt
                    else:
                        mod["flash_timer"] += dt
                        if mod["flash_timer"] >= 0.6:
                            mod["flash_timer"] = 0.0
                            mod["flash_index"] += 1
                            if mod["flash_index"] >= mod["stage"]:
                                mod["show_count"] += 1
                                mod["flash_index"] = 0
                                if mod["show_count"] >= 2:
                                    mod["phase"] = "input"
                                else:
                                    mod["pause_timer"] = 0.5
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
        elif mod["type"] == "morse":
            self._draw_morse_module(screen, mod)
        elif mod["type"] == "simon":
            self._draw_simon_module(screen, mod)
        elif mod["type"] == "numpad":
            self._draw_numpad_module(screen, mod)

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

    def _draw_morse_module(self, screen, mod):
        header = self.font_med.render("MORSE CODE", True, COLORS["white"])
        screen.blit(header, (40, 130))

        info = self.font_sm.render("Read the morse code to your team, then set the frequency", True, COLORS["grey"])
        screen.blit(info, (40, 170))

        morse_str = mod["morse"]
        total_len = len(morse_str)
        if total_len > 0:
            cycle_time = total_len * 0.3 + 2.0
            pos = mod["flash_timer"] % cycle_time
            char_idx = int(pos / 0.3)
            if char_idx < total_len:
                current_char = morse_str[char_idx]
                if current_char == ".":
                    light_color = COLORS["yellow"]
                    light_size = 20
                elif current_char == "-":
                    light_color = COLORS["yellow"]
                    light_size = 40
                else:
                    light_color = (40, 40, 45)
                    light_size = 20
            else:
                light_color = (40, 40, 45)
                light_size = 20

            cx = SCREEN_WIDTH // 2
            pygame.draw.circle(screen, light_color, (cx, 240), light_size)
            pygame.draw.circle(screen, COLORS["white"], (cx, 240), light_size, 2)

        morse_display = self.font_sm.render(f"Signal: {morse_str}", True, COLORS["yellow"])
        screen.blit(morse_display, morse_display.get_rect(centerx=SCREEN_WIDTH // 2, y=280))

        freq_text = f"Frequency: {mod['selected_freq']:.3f} MHz"
        freq_surf = self.font_big.render(freq_text, True, COLORS["green"])
        screen.blit(freq_surf, freq_surf.get_rect(centerx=SCREEN_WIDTH // 2, y=340))

        bar_w = 500
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = 420
        pygame.draw.rect(screen, (40, 40, 45), (bar_x, bar_y, bar_w, 20))
        frac = (mod["selected_freq"] - 3.500) / 0.100
        marker_x = bar_x + int(frac * bar_w)
        pygame.draw.rect(screen, COLORS["green"], (marker_x - 3, bar_y - 5, 6, 30))

        range_l = self.font_mono.render("3.500", True, COLORS["grey"])
        range_r = self.font_mono.render("3.600", True, COLORS["grey"])
        screen.blit(range_l, (bar_x, bar_y + 25))
        screen.blit(range_r, (bar_x + bar_w - range_r.get_width(), bar_y + 25))

        hint = self.font_mono.render("UP/DOWN=tune  GREEN=submit", True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=470))

    def _draw_simon_module(self, screen, mod):
        header = self.font_med.render("SIMON SAYS", True, COLORS["white"])
        screen.blit(header, (40, 130))

        stage_text = f"Stage {mod['stage']} of {len(mod['sequence'])}"
        stage_surf = self.font_sm.render(stage_text, True, COLORS["white"])
        screen.blit(stage_surf, (40, 170))

        positions = {
            "RED": (SCREEN_WIDTH // 2, 230),
            "BLUE": (SCREEN_WIDTH // 2 + 120, 310),
            "GREEN": (SCREEN_WIDTH // 2, 390),
            "YELLOW": (SCREEN_WIDTH // 2 - 120, 310),
        }
        button_labels = {"RED": "UP", "BLUE": "START", "GREEN": "DOWN", "YELLOW": "GREEN"}

        active_color = None
        if mod["phase"] == "showing" and mod["pause_timer"] <= 0:
            if mod["flash_index"] < mod["stage"]:
                flash_half = mod["flash_timer"] < 0.4
                if flash_half:
                    active_color = mod["sequence"][mod["flash_index"]]

        for color_name, (cx, cy) in positions.items():
            if color_name == active_color:
                rgb = SIMON_RGB[color_name]
            else:
                rgb = SIMON_DIM_RGB[color_name]
            pygame.draw.circle(screen, rgb, (cx, cy), 45)
            pygame.draw.circle(screen, COLORS["white"], (cx, cy), 45, 2)
            label = self.font_mono.render(color_name, True, COLORS["white"])
            screen.blit(label, label.get_rect(center=(cx, cy - 8)))
            btn = self.font_mono.render(f"[{button_labels[color_name]}]", True, COLORS["grey"])
            screen.blit(btn, btn.get_rect(center=(cx, cy + 12)))

        if mod["phase"] == "showing":
            status = self.font_sm.render("WATCH THE SEQUENCE...", True, COLORS["yellow"])
        else:
            status = self.font_sm.render(
                f"YOUR TURN — {len(mod['input'])}/{mod['stage']} entered",
                True, COLORS["green"],
            )
        screen.blit(status, status.get_rect(centerx=SCREEN_WIDTH // 2, y=460))

    def _draw_numpad_module(self, screen, mod):
        header = self.font_med.render("NUMBER PAD", True, COLORS["white"])
        screen.blit(header, (40, 130))

        info = self.font_sm.render("Tell your team the display and lit indicators", True, COLORS["grey"])
        screen.blit(info, (40, 170))

        display_rect = pygame.Rect(SCREEN_WIDTH // 2 - 60, 210, 120, 80)
        pygame.draw.rect(screen, (20, 20, 30), display_rect)
        pygame.draw.rect(screen, COLORS["white"], display_rect, 2)
        num_surf = self.font_big.render(str(mod["display_number"]), True, COLORS["green"])
        screen.blit(num_surf, num_surf.get_rect(center=display_rect.center))

        ind_x = 40
        ind_y = 320
        ind_label = self.font_sm.render("Indicators:", True, COLORS["white"])
        screen.blit(ind_label, (ind_x, ind_y - 30))
        for ind_name, lit in mod["indicators"].items():
            color = COLORS["green"] if lit else COLORS["dark_grey"]
            pygame.draw.circle(screen, color, (ind_x + 10, ind_y + 10), 8)
            pygame.draw.circle(screen, COLORS["white"], (ind_x + 10, ind_y + 10), 8, 1)
            label = self.font_mono.render(ind_name, True, COLORS["white"] if lit else COLORS["grey"])
            screen.blit(label, (ind_x + 25, ind_y))
            ind_x += 120

        answer_y = 390
        answer_label = self.font_sm.render("Select answer:", True, COLORS["white"])
        screen.blit(answer_label, (40, answer_y))

        for i, opt in enumerate(mod["options"]):
            is_selected = i == mod["selected"]
            x = 60 + i * 120
            y = answer_y + 40

            btn_rect = pygame.Rect(x, y, 80, 60)
            btn_color = COLORS["yellow"] if is_selected else (40, 40, 50)
            pygame.draw.rect(screen, btn_color, btn_rect, border_radius=6)
            pygame.draw.rect(screen, COLORS["white"], btn_rect, 2, border_radius=6)

            text_color = COLORS["bg"] if is_selected else COLORS["white"]
            num = self.font_med.render(str(opt), True, text_color)
            screen.blit(num, num.get_rect(center=btn_rect.center))

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

        elapsed = self.play_end_time - self.play_start_time
        stats = self.font_sm.render(
            f"Strikes: {self.strikes}  |  Time: {int(elapsed) // 60}m{int(elapsed) % 60:02d}s",
            True, COLORS["white"],
        )
        screen.blit(stats, stats.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60)))

        prompt = self.font_sm.render("Press START to play again", True, COLORS["grey"])
        screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100)))

    def _save_history(self):
        self.play_end_time = time.time()
        elapsed = self.play_end_time - self.play_start_time
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
