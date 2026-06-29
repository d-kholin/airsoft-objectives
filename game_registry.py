"""Registry of available game modes and their configurable settings."""

from presets import (
    CUSTOM_MIN_MINUTES,
    CUSTOM_MAX_MINUTES,
    COUNTDOWN_PRESETS,
    DISARM_PRESETS,
    MODULE_PRESETS,
    PHASE_PRESETS,
    registry_options,
    timer_presets,
)

TIMER_OPTIONS = registry_options(timer_presets())
TIMER_OPTIONS_WITH_OFF = registry_options(timer_presets(include_off=True))
MODULE_OPTIONS = registry_options(MODULE_PRESETS)
COUNTDOWN_OPTIONS = registry_options(COUNTDOWN_PRESETS)
DISARM_OPTIONS = registry_options(DISARM_PRESETS)
PHASE_OPTIONS = registry_options(PHASE_PRESETS)

_CUSTOM = {"custom_min": CUSTOM_MIN_MINUTES, "custom_max": CUSTOM_MAX_MINUTES}

GAME_MODES = {
    "comms_hack": {
        "name": "Comms Array Hack",
        "description": "Enter 3 codes to hack the comms array before time runs out",
        "settings": {
            "timer": {
                "label": "Timer",
                "type": "choice",
                "options": TIMER_OPTIONS_WITH_OFF,
                "default": 300,
                **_CUSTOM,
            }
        },
    },
    "bomb_defusal": {
        "name": "Bomb Defusal",
        "description": "Solve modules and defuse the bomb before time runs out",
        "settings": {
            "timer": {
                "label": "Timer",
                "type": "choice",
                "options": TIMER_OPTIONS,
                "default": 900,
                **_CUSTOM,
            },
            "modules": {
                "label": "Modules",
                "type": "choice",
                "options": MODULE_OPTIONS,
                "default": 4,
            },
        },
    },
    "domination": {
        "name": "Domination",
        "description": "Two teams fight to hold the objective — first to the goal wins",
        "settings": {
            "goal_time": {
                "label": "Goal Time",
                "type": "choice",
                "options": TIMER_OPTIONS,
                "default": 600,
                **_CUSTOM,
            }
        },
    },
    "missile_launch": {
        "name": "Missile Launch",
        "description": "Fuel, raise, and arm the missile — then enter launch codes before the enemy stops you",
        "settings": {
            "game_time": {
                "label": "Game Time",
                "type": "choice",
                "options": TIMER_OPTIONS,
                "default": 900,
                **_CUSTOM,
            },
            "fuel_time": {
                "label": "Fuel Duration",
                "type": "choice",
                "options": PHASE_OPTIONS,
                "default": 240,
                **_CUSTOM,
            },
            "raise_time": {
                "label": "Raise Duration",
                "type": "choice",
                "options": PHASE_OPTIONS,
                "default": 240,
                **_CUSTOM,
            },
            "arm_time": {
                "label": "Arm Duration",
                "type": "choice",
                "options": PHASE_OPTIONS,
                "default": 180,
                **_CUSTOM,
            },
            "countdown": {
                "label": "Launch Countdown",
                "type": "choice",
                "options": COUNTDOWN_OPTIONS,
                "default": 120,
                **_CUSTOM,
            },
        },
    },
}


def get_mode_info(mode_id):
    """Get info for a specific mode, or None if not found."""
    return GAME_MODES.get(mode_id)


def get_mode_class(mode_id):
    """Import and return the GameMode class for a mode."""
    if mode_id == "comms_hack":
        from modes.comms_hack import CommsHackMode
        return CommsHackMode
    elif mode_id == "bomb_defusal":
        from modes.bomb_defusal import BombDefusalMode
        return BombDefusalMode
    elif mode_id == "domination":
        from modes.domination import DominationMode
        return DominationMode
    elif mode_id == "missile_launch":
        from modes.missile_launch import MissileLaunchMode
        return MissileLaunchMode
    return None


def list_modes():
    """Return list of all available modes."""
    return list(GAME_MODES.keys())
