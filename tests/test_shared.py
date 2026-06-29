"""Tests for the shared helper modules extracted from the game modes."""

import unittest

import history
from presets import (
    TIMER_PRESETS,
    timer_presets,
    registry_options,
    CUSTOM_MAX_MINUTES,
)
from game_registry import GAME_MODES


class PresetsTest(unittest.TestCase):
    def test_off_is_prepended_only_when_requested(self):
        self.assertEqual(timer_presets()[0], ("5 MIN", 300))
        self.assertEqual(timer_presets(include_off=True)[0], ("OFF", 0))

    def test_custom_sentinel_maps_to_minus_one(self):
        opts = registry_options(timer_presets())
        custom = [o for o in opts if o["label"] == "CUSTOM"]
        self.assertEqual(custom, [{"label": "CUSTOM", "value": -1}])

    def test_registry_reuses_shared_presets(self):
        # The timer options in the web registry must come from the single shared
        # preset list — the source of the original README/runtime drift.
        shared_labels = [label for label, _ in TIMER_PRESETS]
        for mode, key in (("bomb_defusal", "timer"), ("domination", "goal_time")):
            labels = [o["label"] for o in GAME_MODES[mode]["settings"][key]["options"]]
            self.assertEqual(labels, shared_labels)

    def test_custom_max_is_two_digits(self):
        self.assertEqual(CUSTOM_MAX_MINUTES, 99)


class HistoryTest(unittest.TestCase):
    MODE = "unittest_tmp_mode"

    def tearDown(self):
        path = history.history_path(self.MODE)
        if path.exists():
            path.unlink()

    def test_round_trip_append_and_load(self):
        self.assertEqual(history.load_history(self.MODE), [])
        history.append_history(self.MODE, {"result": "victory", "n": 1})
        history.append_history(self.MODE, {"result": "defeat", "n": 2})
        entries = history.load_history(self.MODE)
        self.assertEqual([e["n"] for e in entries], [1, 2])

    def test_corrupt_file_loads_as_empty(self):
        path = history.history_path(self.MODE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{ not valid json")
        self.assertEqual(history.load_history(self.MODE), [])


if __name__ == "__main__":
    unittest.main()
