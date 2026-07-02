import pygame
import math
import random
import time
from game_mode import GameMode
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT
from ui import draw_menu_item
from widgets import draw_7seg_time, seg7_width, handle_custom_timer, draw_custom_timer
from presets import timer_presets, MODULE_PRESETS

TIMER_PRESETS = timer_presets()

WIRE_COLORS = ["RED", "BLUE", "YELLOW", "WHITE", "GREEN"]
WIRE_RGB = {
    "RED": (255, 40, 40),
    "BLUE": (40, 100, 255),
    "YELLOW": (255, 220, 0),
    "WHITE": (240, 240, 240),
    "GREEN": (0, 200, 80),
}

# Columns are designed so every pair shares at most 3 symbols. This guarantees
# any 4-symbol puzzle drawn from one column maps to exactly one column (no
# ambiguity for the manual). See scratchpad/gen_keypad.py for the search.
KEYPAD_COLUMNS = [
    ["NOVA", "SAGE", "BOLT", "APEX", "QUAD", "DROP", "GEAR"],
    ["RING", "HALO", "COIL", "STAR", "GRID", "FANG", "REEF"],
    ["PYRE", "DART", "FANG", "QUAD", "STAR", "APEX", "NOVA"],
    ["TIDE", "GRID", "STAR", "REEF", "PYRE", "WISP", "APEX"],
    ["GRID", "PYRE", "COIL", "KNOT", "QUAD", "GEAR", "NOVA"],
    ["FANG", "WAVE", "TIDE", "HALO", "NOVA", "WISP", "KNOT"],
]

BUTTON_COLORS = ["RED", "BLUE", "YELLOW", "WHITE"]
BUTTON_LABELS = ["ABORT", "DETONATE", "HOLD", "PRESS", "DISARM"]

CAP_COLORS = ["RED", "BLUE", "GREEN", "YELLOW"]
CAP_COLOR_RGB = {
    "RED": (255, 40, 40),
    "BLUE": (40, 100, 255),
    "GREEN": (0, 200, 80),
    "YELLOW": (255, 220, 0),
}

PIN_STATUSES = ["ARMED", "SAFE", "UNKNOWN"]
PIN_STATUS_COLOR = {
    "ARMED": (255, 40, 40),
    "SAFE": (0, 200, 80),
    "UNKNOWN": (255, 220, 0),
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
        if wires[-1] == "GREEN" and _serial_last_odd(serial):
            return 3
        elif wires.count("RED") == 1 and wires.count("YELLOW") > 1:
            return 0
        elif "GREEN" not in wires:
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


def _generate_capacitor_module():
    count = random.randint(3, 4)
    voltages = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    all_combos = [(c, v) for c in CAP_COLORS for v in voltages]
    chosen = random.sample(all_combos, count)
    caps = []
    for color, voltage in chosen:
        caps.append({"color": color, "voltage": voltage, "discharged": False})
    return {
        "type": "capacitor",
        "capacitors": caps,
        "discharge_step": 0,
        "solved": False,
        "selected": 0,
    }


def _solve_capacitor_order(caps, serial, indicators):
    color_priority = {"RED": 0, "YELLOW": 1, "BLUE": 2, "GREEN": 3}
    indexed = list(enumerate(caps))
    has_frk = "FRK" in indicators
    has_car = "CAR" in indicators
    has_vowel = _serial_has_vowel(serial)
    last_odd = _serial_last_odd(serial)

    if has_frk and has_car:
        indexed.sort(key=lambda ic: (
            color_priority.get(ic[1]["color"], 9), ic[1]["voltage"]
        ))
    elif has_frk:
        indexed.sort(key=lambda ic: (
            -ic[1]["voltage"], color_priority.get(ic[1]["color"], 9)
        ))
    elif has_vowel and last_odd:
        reds = [ic for ic in indexed if ic[1]["color"] == "RED"]
        others = [ic for ic in indexed if ic[1]["color"] != "RED"]
        others.sort(key=lambda ic: (ic[1]["voltage"], color_priority.get(ic[1]["color"], 9)))
        reds.sort(key=lambda ic: ic[1]["voltage"])
        indexed = others + reds
    else:
        indexed.sort(key=lambda ic: (
            ic[1]["voltage"], color_priority.get(ic[1]["color"], 9)
        ))

    return [i for i, _ in indexed]


def _generate_pins_module():
    count = random.randint(4, 5)
    pins = []
    statuses = ["ARMED", "ARMED", "SAFE", "UNKNOWN", "UNKNOWN"]
    random.shuffle(statuses)
    for i in range(count):
        pins.append({"number": i + 1, "status": statuses[i], "pulled": False})
    return {
        "type": "pins",
        "pins": pins,
        "solved": False,
        "selected": 0,
        "pull_step": 0,
    }


def _solve_pins_order(pins, serial):
    last_odd = _serial_last_odd(serial)
    has_vowel = _serial_has_vowel(serial)
    armed = [p for p in pins if p["status"] == "ARMED"]
    unknown = [p for p in pins if p["status"] == "UNKNOWN"]
    safe = [p for p in pins if p["status"] == "SAFE"]

    order = []
    if last_odd:
        order.extend(sorted(unknown, key=lambda p: p["number"]))
        order.extend(sorted(armed, key=lambda p: p["number"], reverse=True))
        order.extend(sorted(safe, key=lambda p: p["number"]))
    elif has_vowel:
        order.extend(sorted(safe, key=lambda p: p["number"]))
        order.extend(sorted(unknown, key=lambda p: p["number"], reverse=True))
        order.extend(sorted(armed, key=lambda p: p["number"]))
    else:
        order.extend(sorted(armed, key=lambda p: p["number"]))
        order.extend(sorted(safe, key=lambda p: p["number"]))
        order.extend(sorted(unknown, key=lambda p: p["number"], reverse=True))

    return [p["number"] for p in order]


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
    mode_id = "bomb_defusal"
    description = "Defuse the bomb with help from your team over radio"

    def setup(self, config=None):
        config = config or {}
        self.font_big = pygame.font.Font(None, 72)
        self.font_med = pygame.font.Font(None, 48)
        self.font_sm = pygame.font.Font(None, 36)
        self.font_mono = pygame.font.Font(None, 28)
        self.timer_selection = 2
        self.custom_minutes = 10
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

        if "timer" in config and "modules" in config:
            self.timer_total = config["timer"]
            self.timer_remaining = self.timer_total
            self.num_modules = config["modules"]
            self._start_game()
        else:
            self.phase = "setup_timer"

    def _is_held(self, action):
        return self.app.input.is_action_held(action)

    def _draw_selector(self, screen, y, h, x=35, w=None):
        if w is None:
            w = SCREEN_WIDTH - 70
        pygame.draw.rect(screen, (60, 60, 20), (x, y, w, h))
        pygame.draw.rect(screen, COLORS["yellow"], (x, y, 6, h))

    def handle_input(self, actions):
        if self.phase == "setup_timer":
            self._handle_setup_timer(actions)
        elif self.phase == "setup_custom":
            self._handle_setup_custom(actions)
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
            preset = TIMER_PRESETS[self.timer_selection][1]
            if preset is None:
                self.phase = "setup_custom"
            else:
                self.timer_total = preset
                self.timer_remaining = self.timer_total
                self.phase = "setup_modules"

    def _handle_setup_custom(self, actions):
        self.custom_minutes, result = handle_custom_timer(actions, self.custom_minutes)
        if result == "back":
            self.phase = "setup_timer"
        elif result == "confirm":
            self.timer_total = self.custom_minutes * 60
            self.timer_remaining = self.timer_total
            self.phase = "setup_modules"

    def _handle_setup_modules(self, actions):
        if "UP" in actions:
            self.module_selection = (self.module_selection - 1) % len(MODULE_PRESETS)
        if "DOWN" in actions:
            self.module_selection = (self.module_selection + 1) % len(MODULE_PRESETS)
        if "START" in actions or "GREEN_BUTTON" in actions:
            self.num_modules = MODULE_PRESETS[self.module_selection][1]
            self._start_game()

    def _start_game(self):
        self._generate_bomb()
        self.phase = "play"
        self.play_start_time = time.time()

    def _generate_bomb(self):
        self.serial = _generate_serial()
        self.indicators = random.sample(NUMPAD_INDICATORS, random.randint(1, 3))
        generators = [
            _generate_wires_module, _generate_keypad_module, _generate_button_module,
            _generate_capacitor_module, _generate_pins_module, _generate_numpad_module,
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
        elif mod["type"] == "capacitor":
            self._handle_capacitor(mod, actions)
        elif mod["type"] == "pins":
            self._handle_pins(mod, actions)
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

    def _update_button_hold(self, mod):
        """Called every frame to track hold/release via real-time key state."""
        if _solve_button_action(mod, self.serial) != "hold":
            return
        green_held = self._is_held("GREEN_BUTTON")
        if green_held and not mod["held"]:
            mod["held"] = True
            mod["phase"] = "holding"
            mod["release_digit"] = _solve_button_release(mod)
        elif not green_held and mod["held"]:
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

    def _skip_discharged_caps(self, mod, direction):
        n = len(mod["capacitors"])
        for _ in range(n):
            mod["selected"] = (mod["selected"] + direction) % n
            if not mod["capacitors"][mod["selected"]]["discharged"]:
                return

    def _handle_capacitor(self, mod, actions):
        if "UP" in actions:
            self._skip_discharged_caps(mod, -1)
        if "DOWN" in actions:
            self._skip_discharged_caps(mod, 1)
        if "GREEN_BUTTON" in actions or "START" in actions:
            cap = mod["capacitors"][mod["selected"]]
            if cap["discharged"]:
                return
            correct_order = _solve_capacitor_order(mod["capacitors"], self.serial, self.indicators)
            expected_idx = correct_order[mod["discharge_step"]]
            if mod["selected"] == expected_idx:
                cap["discharged"] = True
                mod["discharge_step"] += 1
                self.app.sound.play("confirm")
                if mod["discharge_step"] == len(mod["capacitors"]):
                    mod["solved"] = True
                    self._check_win()
            else:
                self._strike()

    def _skip_pulled_pins(self, mod, direction):
        n = len(mod["pins"])
        for _ in range(n):
            mod["selected"] = (mod["selected"] + direction) % n
            if not mod["pins"][mod["selected"]]["pulled"]:
                return

    def _handle_pins(self, mod, actions):
        if "UP" in actions:
            self._skip_pulled_pins(mod, -1)
        if "DOWN" in actions:
            self._skip_pulled_pins(mod, 1)
        if "GREEN_BUTTON" in actions or "START" in actions:
            pin = mod["pins"][mod["selected"]]
            if pin["pulled"]:
                return
            correct_order = _solve_pins_order(mod["pins"], self.serial)
            expected_pin_num = correct_order[mod["pull_step"]]
            if pin["number"] == expected_pin_num:
                pin["pulled"] = True
                mod["pull_step"] += 1
                self.app.sound.play("confirm")
                if mod["pull_step"] == len(mod["pins"]):
                    mod["solved"] = True
                    self._check_win()
            else:
                self._strike()

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
            self.timer_remaining -= dt
            if self.timer_remaining <= 0:
                self.timer_remaining = 0
                self.result = "defeat"
                self.phase = "result"
                self.pulse_time = 0.0
                self._save_history()
                self.app.sound.play("defeat")
            else:
                for mod in self.modules:
                    if not mod["solved"] and mod["type"] == "button":
                        self._update_button_hold(mod)
        if self.phase == "result":
            self.pulse_time += dt

    def draw(self, screen):
        if self.phase == "setup_timer":
            self._draw_setup_timer(screen)
        elif self.phase == "setup_custom":
            self._draw_setup_custom(screen)
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

        col_x = [200, 560]
        row_h = 64
        top = 148
        per_col = (len(TIMER_PRESETS) + 1) // 2
        for i, (label, _) in enumerate(TIMER_PRESETS):
            x = col_x[i // per_col]
            y = top + (i % per_col) * row_h
            draw_menu_item(screen, self.font_med, label, i == self.timer_selection, x, y)

        hints = self.font_sm.render("UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_setup_custom(self, screen):
        draw_custom_timer(
            screen, self.font_big, self.font_sm, "BOMB DEFUSAL SETUP",
            self.custom_minutes,
        )

    def _draw_setup_modules(self, screen):
        title = self.font_big.render("BOMB DEFUSAL SETUP", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        sub = self.font_sm.render("Set number of modules", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=90))

        row_h = 64
        x = SCREEN_WIDTH // 2 - 150
        for i, (label, _) in enumerate(MODULE_PRESETS):
            y = 150 + i * row_h
            draw_menu_item(screen, self.font_med, label, i == self.module_selection, x, y)

        hints = self.font_sm.render("UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_play(self, screen):
        # Header background
        pygame.draw.rect(screen, (15, 5, 5), (0, 0, SCREEN_WIDTH, 90))

        # Strikes (left side)
        strike_text = "X " * self.strikes + "O " * (self.max_strikes - self.strikes)
        strike_surf = self.font_sm.render(f"STRIKES: {strike_text}", True, COLORS["red"])
        screen.blit(strike_surf, (15, 8))

        # Serial number (right side)
        serial_surf = self.font_sm.render(f"S/N: {self.serial}", True, COLORS["white"])
        screen.blit(serial_surf, serial_surf.get_rect(right=SCREEN_WIDTH - 15, y=8))

        # 7-segment timer (centered)
        timer_w = seg7_width(w=28, thick=5, gap=5)
        timer_x = (SCREEN_WIDTH - timer_w) // 2
        timer_color = COLORS["red"] if self.timer_remaining < 120 else COLORS["green"]
        draw_7seg_time(screen, timer_x, 16, self.timer_remaining, timer_color,
                       w=28, h=52, thick=5, gap=5)

        pygame.draw.line(screen, DIM_RED, (0, 90), (SCREEN_WIDTH, 90))

        # Module tabs
        tab_y = 95
        tab_x = 15
        for i, mod in enumerate(self.modules):
            is_current = i == self.current_module
            holding = mod["type"] == "button" and mod.get("held")
            if mod["solved"]:
                color = COLORS["green"]
                label = f"[{i+1}] OK"
            elif is_current:
                color = COLORS["yellow"]
                label = f"[{i+1}] {mod['type'].upper()}"
            else:
                color = COLORS["red"] if holding else COLORS["grey"]
                label = f"[{i+1}] {mod['type'].upper()}"
            if holding:
                label += " (HOLDING)"
            surf = self.font_sm.render(label, True, color)
            screen.blit(surf, (tab_x, tab_y))
            tab_x += surf.get_width() + 20

        pygame.draw.line(screen, DIM_RED, (0, 125), (SCREEN_WIDTH, 125))

        # Current module content
        mod = self.modules[self.current_module]
        if mod["solved"]:
            solved_surf = self.font_big.render("MODULE DISARMED", True, COLORS["green"])
            screen.blit(solved_surf, solved_surf.get_rect(center=(SCREEN_WIDTH // 2, 350)))
        elif mod["type"] == "wires":
            self._draw_wires_module(screen, mod)
        elif mod["type"] == "keypad":
            self._draw_keypad_module(screen, mod)
        elif mod["type"] == "button":
            self._draw_button_module(screen, mod)
        elif mod["type"] == "capacitor":
            self._draw_capacitor_module(screen, mod)
        elif mod["type"] == "pins":
            self._draw_pins_module(screen, mod)
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
                self._draw_selector(screen, y - 5, 45)

            wire_color = WIRE_RGB[color_name]
            pygame.draw.rect(screen, wire_color, (80, y + 8, 400, 12))
            pygame.draw.rect(screen, wire_color, (60, y, 20, 28), border_radius=4)
            pygame.draw.rect(screen, wire_color, (480, y, 20, 28), border_radius=4)

            label = self.font_sm.render(f"{i+1}. {color_name}", True, COLORS["white"] if is_selected else COLORS["grey"])
            screen.blit(label, (520, y + 2))

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
                self._draw_selector(screen, y - 5, 50, w=350)

            if already_pressed:
                color = COLORS["green"]
                prefix = "[OK] "
            elif is_selected:
                color = COLORS["white"]
                prefix = "     "
            else:
                color = COLORS["grey"]
                prefix = "     "

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
                "HOLDING — release GREEN to release", True, COLORS["yellow"]
            )
            screen.blit(hold_info, hold_info.get_rect(centerx=SCREEN_WIDTH // 2, y=410))
            hint = self.font_mono.render(
                "Check manual for when to release based on strip color",
                True, COLORS["grey"],
            )
            screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=445))
        else:
            action_hint = self.font_sm.render(
                "GREEN = tap the button  |  hold GREEN to hold & release",
                True, COLORS["grey"],
            )
            screen.blit(action_hint, action_hint.get_rect(centerx=SCREEN_WIDTH // 2, y=400))

    def _draw_capacitor_module(self, screen, mod):
        header = self.font_med.render("CAPACITORS", True, COLORS["white"])
        screen.blit(header, (40, 130))

        info = self.font_sm.render(
            "Report colors, voltages, and indicators to your team", True, COLORS["grey"]
        )
        screen.blit(info, (40, 170))

        progress = self.font_sm.render(
            f"Discharged: {mod['discharge_step']}/{len(mod['capacitors'])}",
            True, COLORS["white"],
        )
        screen.blit(progress, progress.get_rect(right=SCREEN_WIDTH - 40, y=130))

        ind_x = 40
        ind_y = 205
        ind_label = self.font_sm.render("Indicators:", True, COLORS["white"])
        screen.blit(ind_label, (ind_x, ind_y))
        ind_x += ind_label.get_width() + 15
        for ind_name in NUMPAD_INDICATORS:
            lit = ind_name in self.indicators
            color = COLORS["green"] if lit else COLORS["dark_grey"]
            pygame.draw.circle(screen, color, (ind_x + 10, ind_y + 12), 8)
            pygame.draw.circle(screen, COLORS["white"], (ind_x + 10, ind_y + 12), 8, 1)
            label = self.font_mono.render(ind_name, True, COLORS["white"] if lit else COLORS["grey"])
            screen.blit(label, (ind_x + 25, ind_y + 3))
            ind_x += 95

        for i, cap in enumerate(mod["capacitors"]):
            y = 250 + i * 75
            is_selected = i == mod["selected"]

            if is_selected and not cap["discharged"]:
                self._draw_selector(screen, y - 5, 70)

            cap_color = CAP_COLOR_RGB[cap["color"]]
            body_rect = pygame.Rect(80, y, 200, 50)

            if cap["discharged"]:
                pygame.draw.rect(screen, (30, 30, 35), body_rect, border_radius=6)
                pygame.draw.rect(screen, (60, 60, 65), body_rect, 2, border_radius=6)
                status_text = "DISCHARGED"
                status_color = COLORS["grey"]
            else:
                pygame.draw.rect(screen, cap_color, body_rect, border_radius=6)
                pygame.draw.rect(screen, COLORS["white"], body_rect, 2, border_radius=6)
                status_text = f"{cap['voltage']:.1f}V"
                status_color = COLORS["white"]

            pygame.draw.rect(screen, cap_color if not cap["discharged"] else (60, 60, 65),
                             (280, y + 15, 30, 20))
            pygame.draw.rect(screen, cap_color if not cap["discharged"] else (60, 60, 65),
                             (50, y + 15, 30, 20))

            label = self.font_sm.render(
                f"{cap['color']}  {status_text}", True, status_color
            )
            screen.blit(label, (340, y + 12))


    def _draw_pins_module(self, screen, mod):
        header = self.font_med.render("DETONATOR PINS", True, COLORS["white"])
        screen.blit(header, (40, 130))

        info = self.font_sm.render(
            "Pull pins in the correct order to disarm", True, COLORS["grey"]
        )
        screen.blit(info, (40, 170))

        progress = self.font_sm.render(
            f"Pulled: {mod['pull_step']}/{len(mod['pins'])}",
            True, COLORS["white"],
        )
        screen.blit(progress, progress.get_rect(right=SCREEN_WIDTH - 40, y=130))

        for i, pin in enumerate(mod["pins"]):
            y = 220 + i * 65
            is_selected = i == mod["selected"]

            if is_selected and not pin["pulled"]:
                self._draw_selector(screen, y - 5, 55)

            if pin["pulled"]:
                pin_rect = pygame.Rect(80, y + 5, 180, 35)
                pygame.draw.rect(screen, (30, 30, 35), pin_rect, border_radius=4)
                pygame.draw.rect(screen, (60, 60, 65), pin_rect, 2, border_radius=4)
                label = self.font_sm.render(
                    f"PIN {pin['number']}  PULLED", True, COLORS["grey"]
                )
            else:
                status_color = PIN_STATUS_COLOR[pin["status"]]
                pin_rect = pygame.Rect(80, y + 5, 180, 35)
                pygame.draw.rect(screen, (20, 20, 25), pin_rect, border_radius=4)
                pygame.draw.rect(screen, status_color, pin_rect, 2, border_radius=4)

                ring = pygame.Rect(260, y + 8, 30, 30)
                pygame.draw.ellipse(screen, status_color, ring, 3)

                label = self.font_sm.render(
                    f"PIN {pin['number']}  [{pin['status']}]", True, status_color
                )

            screen.blit(label, (340, y + 10))

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
        self.save_history({
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "result": self.result,
            "elapsed_seconds": round(elapsed),
            "strikes": self.strikes,
            "modules_total": len(self.modules),
            "modules_solved": sum(1 for m in self.modules if m["solved"]),
            "timer_preset": self.timer_total,
        })
