"""Registry of available game modes and their configurable settings."""

TIMER_OPTIONS = [
    {"label": "5 MIN", "value": 300},
    {"label": "10 MIN", "value": 600},
    {"label": "15 MIN", "value": 900},
    {"label": "20 MIN", "value": 1200},
    {"label": "25 MIN", "value": 1500},
    {"label": "30 MIN", "value": 1800},
    {"label": "CUSTOM", "value": -1},
]

GAME_MODES = {
    "comms_hack": {
        "name": "Comms Array Hack",
        "description": "Enter 3 codes to hack the comms array before time runs out",
        "settings": {
            "timer": {
                "label": "Timer",
                "type": "choice",
                "options": [{"label": "OFF", "value": 0}] + TIMER_OPTIONS,
                "default": 300,
                "custom_min": 1,
                "custom_max": 99,
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
                "custom_min": 1,
                "custom_max": 99,
            },
            "modules": {
                "label": "Modules",
                "type": "choice",
                "options": [
                    {"label": "3 MODULES", "value": 3},
                    {"label": "4 MODULES", "value": 4},
                    {"label": "5 MODULES", "value": 5},
                    {"label": "6 MODULES", "value": 6},
                ],
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
                "custom_min": 1,
                "custom_max": 99,
            }
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
    return None


def list_modes():
    """Return list of all available modes."""
    return list(GAME_MODES.keys())
