import sys
from app import App

if __name__ == "__main__":
    fullscreen = "--windowed" not in sys.argv
    App(fullscreen).run()
