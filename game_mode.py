from history import load_history, append_history


class GameMode:
    name = "Unnamed"
    description = ""
    # Identifier used for history files and the web registry. Subclasses that
    # record history must set this (e.g. "bomb_defusal").
    mode_id = None

    def __init__(self, app):
        self.app = app

    def setup(self, config=None):
        pass

    def handle_input(self, actions):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

    def teardown(self):
        pass

    def save_history(self, entry):
        """Append a result entry to this mode's history file."""
        append_history(self.mode_id, entry)

    @classmethod
    def load_history(cls):
        """Return this mode's stored history entries."""
        return load_history(cls.mode_id)
