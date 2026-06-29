"""Regression tests asserting the Bomb Defusal solver logic matches the
printed defusal manual (docs/bomb_defusal_manual.md).

Each ``manual_*`` function below is an independent transcription of the rules
from the manual text. If the gameplay code (modes/bomb_defusal.py) ever drifts
from the manual the expert team reads, these tests fail — keeping the on-screen
puzzle and the radio manual in agreement.
"""

import itertools
import random
import unittest

from modes.bomb_defusal import (
    KEYPAD_COLUMNS,
    WIRE_COLORS,
    BUTTON_COLORS,
    BUTTON_LABELS,
    NUMPAD_INDICATORS,
    _solve_wires,
    _solve_button_action,
    _solve_button_release,
    _solve_capacitor_order,
    _solve_pins_order,
    _solve_numpad,
    _generate_capacitor_module,
    _generate_pins_module,
)

ODD_SERIAL = "AB1231"      # last digit odd, contains vowel A
EVEN_VOWEL = "AB1230"      # last digit even, contains vowel A
EVEN_NOVOW = "BC1230"      # last digit even, no vowel
_COLOR_PRIORITY = {"RED": 0, "YELLOW": 1, "BLUE": 2, "GREEN": 3}


def _last_odd(serial):
    return int(serial[-1]) % 2 == 1


def _has_vowel(serial):
    return any(c in "AEIOU" for c in serial)


# --- Manual transcriptions -------------------------------------------------

def manual_wires(wires, serial):
    """Returns 0-based index of the wire to cut, per MODULE 1."""
    n = len(wires)
    odd = _last_odd(serial)
    if n == 3:
        if "RED" not in wires:
            return 1            # cut 2nd
        if wires[-1] == "WHITE":
            return n - 1        # cut last
        return 0                # cut 1st
    if n == 4:
        if wires.count("RED") > 1 and odd:
            return max(i for i, w in enumerate(wires) if w == "RED")  # last RED
        if wires[-1] == "YELLOW" and wires.count("RED") == 0:
            return 0
        if wires.count("BLUE") == 1:
            return 0
        return 1
    if n == 5:
        if wires[-1] == "GREEN" and odd:
            return 3
        if wires.count("RED") == 1 and wires.count("YELLOW") > 1:
            return 0
        if "GREEN" not in wires:
            return 1
        return 0
    # n == 6
    if "YELLOW" not in wires and odd:
        return 2
    if wires.count("YELLOW") == 1 and wires.count("WHITE") > 1:
        return 3
    if "RED" not in wires:
        return n - 1
    return 3


def manual_button_action(color, label, serial):
    if color == "BLUE" and label == "ABORT":
        return "hold"
    if label == "DETONATE":
        return "press"
    if color == "WHITE" and _has_vowel(serial):
        return "hold"
    if color == "RED" and label == "HOLD":
        return "press"
    return "hold"


def manual_button_release(color):
    return {"BLUE": 4, "YELLOW": 5}.get(color, 1)


def manual_capacitor_order(caps, serial, indicators):
    """Returns list of original indices in discharge order, per MODULE 4."""
    has_frk = "FRK" in indicators
    has_car = "CAR" in indicators
    idx = list(enumerate(caps))
    if has_frk and has_car:                                   # Rule Set A
        idx.sort(key=lambda ic: (_COLOR_PRIORITY[ic[1]["color"]], ic[1]["voltage"]))
    elif has_frk:                                             # Rule Set B
        idx.sort(key=lambda ic: (-ic[1]["voltage"], _COLOR_PRIORITY[ic[1]["color"]]))
    elif _has_vowel(serial) and _last_odd(serial):            # Rule Set C
        non_red = sorted((ic for ic in idx if ic[1]["color"] != "RED"),
                         key=lambda ic: (ic[1]["voltage"], _COLOR_PRIORITY[ic[1]["color"]]))
        red = sorted((ic for ic in idx if ic[1]["color"] == "RED"),
                     key=lambda ic: ic[1]["voltage"])
        idx = non_red + red
    else:                                                     # Rule Set D
        idx.sort(key=lambda ic: (ic[1]["voltage"], _COLOR_PRIORITY[ic[1]["color"]]))
    return [i for i, _ in idx]


def manual_pins_order(pins, serial):
    """Returns pin numbers in pull order, per MODULE 5."""
    by_status = {s: [p for p in pins if p["status"] == s]
                 for s in ("ARMED", "SAFE", "UNKNOWN")}
    asc = lambda group: sorted(group, key=lambda p: p["number"])
    desc = lambda group: sorted(group, key=lambda p: p["number"], reverse=True)
    if _last_odd(serial):
        order = asc(by_status["UNKNOWN"]) + desc(by_status["ARMED"]) + asc(by_status["SAFE"])
    elif _has_vowel(serial):
        order = asc(by_status["SAFE"]) + desc(by_status["UNKNOWN"]) + asc(by_status["ARMED"])
    else:
        order = asc(by_status["ARMED"]) + asc(by_status["SAFE"]) + desc(by_status["UNKNOWN"])
    return [p["number"] for p in order]


def manual_numpad(display, lit, serial):
    odd = _last_odd(serial)
    has = lambda x: x in lit
    if display == 1:
        if has("FRK") and odd:
            return 3
        if has("CAR"):
            return 4
        return 2
    if display == 2:
        if has("SIG") and has("FRK"):
            return 4
        if odd:
            return 1
        return 3
    if display == 3:
        if has("CAR") and not odd:
            return 1
        if has("SIG"):
            return 2
        return 4
    # display == 4
    if has("FRK") and has("CAR"):
        return 2
    if has("SIG") and odd:
        return 3
    return 1


# --- The manual table, transcribed straight from the doc -------------------

MANUAL_KEYPAD_TABLE = [
    ["NOVA", "SAGE", "BOLT", "APEX", "QUAD", "DROP", "GEAR"],
    ["RING", "HALO", "COIL", "STAR", "GRID", "FANG", "REEF"],
    ["PYRE", "DART", "FANG", "QUAD", "STAR", "APEX", "NOVA"],
    ["TIDE", "GRID", "STAR", "REEF", "PYRE", "WISP", "APEX"],
    ["GRID", "PYRE", "COIL", "KNOT", "QUAD", "GEAR", "NOVA"],
    ["FANG", "WAVE", "TIDE", "HALO", "NOVA", "WISP", "KNOT"],
]


class WiresTest(unittest.TestCase):
    def test_all_combinations_match_manual(self):
        for n in (3, 4, 5, 6):
            for wires in itertools.product(WIRE_COLORS, repeat=n):
                wires = list(wires)
                for serial in (ODD_SERIAL, EVEN_VOWEL, EVEN_NOVOW):
                    self.assertEqual(
                        _solve_wires({"wires": wires}, serial),
                        manual_wires(wires, serial),
                        msg=f"wires={wires} serial={serial}",
                    )


class ButtonTest(unittest.TestCase):
    def test_action_matches_manual(self):
        for color in BUTTON_COLORS:
            for label in BUTTON_LABELS:
                for serial in (ODD_SERIAL, EVEN_VOWEL, EVEN_NOVOW):
                    self.assertEqual(
                        _solve_button_action({"color": color, "label": label}, serial),
                        manual_button_action(color, label, serial),
                        msg=f"color={color} label={label} serial={serial}",
                    )

    def test_release_matches_manual(self):
        for color in ("RED", "BLUE", "YELLOW", "WHITE", "GREEN"):
            self.assertEqual(
                _solve_button_release({"color": color}),
                manual_button_release(color),
            )


class CapacitorTest(unittest.TestCase):
    def test_random_orders_match_manual(self):
        rng = random.Random(20240628)
        for _ in range(3000):
            caps = _generate_capacitor_module()["capacitors"]
            serial = rng.choice([ODD_SERIAL, EVEN_VOWEL, EVEN_NOVOW])
            indicators = rng.sample(NUMPAD_INDICATORS, rng.randint(0, 3))
            self.assertEqual(
                _solve_capacitor_order(caps, serial, indicators),
                manual_capacitor_order(caps, serial, indicators),
                msg=f"caps={caps} serial={serial} ind={indicators}",
            )


class PinsTest(unittest.TestCase):
    def test_random_orders_match_manual(self):
        rng = random.Random(13371337)
        for _ in range(3000):
            pins = _generate_pins_module()["pins"]
            serial = rng.choice([ODD_SERIAL, EVEN_VOWEL, EVEN_NOVOW])
            self.assertEqual(
                _solve_pins_order(pins, serial),
                manual_pins_order(pins, serial),
                msg=f"pins={pins} serial={serial}",
            )


class NumpadTest(unittest.TestCase):
    def test_all_combinations_match_manual(self):
        relevant = ["SIG", "FRK", "CAR"]
        for display in (1, 2, 3, 4):
            for r in range(len(relevant) + 1):
                for lit in itertools.combinations(relevant, r):
                    for serial in (ODD_SERIAL, EVEN_NOVOW):
                        module = {"display_number": display, "lit_indicators": list(lit)}
                        self.assertEqual(
                            _solve_numpad(module, serial),
                            manual_numpad(display, set(lit), serial),
                            msg=f"display={display} lit={lit} serial={serial}",
                        )


class KeypadTest(unittest.TestCase):
    def test_columns_match_manual(self):
        # The on-screen columns must equal the manual's printed table.
        self.assertEqual(KEYPAD_COLUMNS, MANUAL_KEYPAD_TABLE)

    def test_every_puzzle_maps_to_exactly_one_column(self):
        # A 4-symbol puzzle sampled from any column must be a subset of exactly
        # one column — otherwise the expert team can't disambiguate it.
        col_sets = [set(c) for c in KEYPAD_COLUMNS]
        for column in KEYPAD_COLUMNS:
            for puzzle in itertools.combinations(set(column), 4):
                matches = sum(1 for cs in col_sets if set(puzzle) <= cs)
                self.assertEqual(matches, 1, msg=f"ambiguous puzzle {puzzle}")


if __name__ == "__main__":
    unittest.main()
