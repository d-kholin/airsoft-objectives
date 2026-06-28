from enum import Enum, auto


class GameState(Enum):
    SETUP = auto()
    RUNNING = auto()
    FINISHED = auto()


class GameMode:
    name = "Unnamed"
    description = ""

    def __init__(self, app):
        self.app = app
        self.state = GameState.SETUP

    def setup(self, config=None):
        self.state = GameState.RUNNING

    def handle_input(self, actions):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass

    def teardown(self):
        self.state = GameState.FINISHED
