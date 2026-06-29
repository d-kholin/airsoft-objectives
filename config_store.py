import json
import threading
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "data" / "comms_config.json"


class ConfigStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {"codes": [], "pin": "1234"}
        self._load()

    def _load(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            try:
                self._data = json.loads(CONFIG_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass

    def _save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(self._data, indent=2))

    def get_codes(self):
        with self._lock:
            return list(self._data.get("codes", []))

    def set_codes(self, codes):
        with self._lock:
            self._data["codes"] = list(codes)
            self._save()

    def clear_codes(self):
        with self._lock:
            self._data["codes"] = []
            self._save()

    def get_pin(self):
        with self._lock:
            return self._data.get("pin", "1234")

    def set_pin(self, pin):
        with self._lock:
            self._data["pin"] = pin
            self._save()
