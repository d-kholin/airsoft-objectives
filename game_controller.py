"""Manages game command and state via shared JSON files."""

import json
import threading
from pathlib import Path

COMMAND_FILE = Path(__file__).parent / "data" / "game_command.json"
STATE_FILE = Path(__file__).parent / "data" / "game_state.json"


class GameController:
    def __init__(self):
        self._lock = threading.Lock()
        COMMAND_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def get_command(self):
        """Get the current queued command (and clear it)."""
        with self._lock:
            if COMMAND_FILE.exists():
                try:
                    cmd = json.loads(COMMAND_FILE.read_text())
                    COMMAND_FILE.unlink()  # Clear after reading
                    return cmd
                except (json.JSONDecodeError, OSError):
                    return None
            return None

    def queue_command(self, mode_id, settings=None, force=False):
        """Queue a game command to be executed by the pygame app."""
        with self._lock:
            cmd = {
                "mode": mode_id,
                "settings": settings or {},
                "force": force,
            }
            COMMAND_FILE.write_text(json.dumps(cmd))

    def get_state(self):
        """Get the current game state."""
        with self._lock:
            if STATE_FILE.exists():
                try:
                    return json.loads(STATE_FILE.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
            return {
                "status": "idle",
                "mode": None,
                "time_remaining": 0,
                "message": "Ready",
            }

    def set_state(self, state):
        """Update the game state (called by pygame app)."""
        with self._lock:
            STATE_FILE.write_text(json.dumps(state))

    def reset_command_file(self):
        """Clear any pending command."""
        with self._lock:
            if COMMAND_FILE.exists():
                COMMAND_FILE.unlink()
