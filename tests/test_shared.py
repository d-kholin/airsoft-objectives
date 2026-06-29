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


class RegistryWiringTest(unittest.TestCase):
    def test_every_registered_mode_resolves_to_a_class(self):
        from game_registry import list_modes, get_mode_class
        for mode_id in list_modes():
            self.assertIsNotNone(get_mode_class(mode_id),
                                 msg=f"{mode_id} has no class mapping")

    def test_missile_has_all_three_timer_settings(self):
        from presets import COUNTDOWN_PRESETS, DISARM_PRESETS
        from game_registry import GAME_MODES
        settings = GAME_MODES["missile_launch"]["settings"]
        self.assertEqual(set(settings), {"game_time", "countdown", "hold_time"})
        self.assertEqual(settings["game_time"]["label"], "Game Time")
        self.assertEqual(
            [o["label"] for o in settings["countdown"]["options"]],
            [label for label, _ in COUNTDOWN_PRESETS])
        self.assertEqual(
            [o["label"] for o in settings["hold_time"]["options"]],
            [label for label, _ in DISARM_PRESETS])
        self.assertEqual(settings["countdown"]["default"], 120)
        self.assertEqual(settings["hold_time"]["default"], 15)


class ConfigStoreTest(unittest.TestCase):
    def test_launch_code_round_trip(self):
        from config_store import ConfigStore
        store = ConfigStore()
        original = store.get_launch_code()
        try:
            store.set_launch_code("ALPHA7")
            self.assertEqual(store.get_launch_code(), "ALPHA7")
            store.clear_launch_code()
            self.assertEqual(store.get_launch_code(), "")
        finally:
            store.set_launch_code(original)


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
