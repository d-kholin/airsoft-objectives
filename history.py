"""Shared game-history persistence.

Each mode stores its results in ``data/<mode_id>_history.json`` as a flat list
of entry dicts. Modes only build the entry; load/append boilerplate lives here.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def history_path(mode_id):
    return DATA_DIR / f"{mode_id}_history.json"


def load_history(mode_id):
    """Return the list of stored entries for a mode (empty if none/unreadable)."""
    path = history_path(mode_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return []


def append_history(mode_id, entry):
    """Append one result entry to a mode's history file."""
    path = history_path(mode_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_history(mode_id)
    history.append(entry)
    path.write_text(json.dumps(history, indent=2))
