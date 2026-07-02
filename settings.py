import pygame

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
FPS = 30

# DragonRise Generic USB Joystick button-to-action mapping.
# Discovered via JoyButtonDown events: button index → action.
BUTTON_MAP = {
    0: "BACK",        # Escape / kill match
    1: "RED_BUTTON",
    2: "BLUE_BUTTON",
    3: "GREEN_BUTTON",
    11: "UP",
    10: "DOWN",
}

# Keyboard fallbacks for dev/testing without the joystick.
KEY_MAP = {
    pygame.K_UP: "UP",
    pygame.K_DOWN: "DOWN",
    pygame.K_1: "RED_BUTTON",
    pygame.K_2: "BLUE_BUTTON",
    pygame.K_3: "GREEN_BUTTON",
    pygame.K_RETURN: "START",
    pygame.K_ESCAPE: "BACK",
}

COLORS = {
    "bg": (10, 10, 15),
    "red": (255, 40, 40),
    "blue": (40, 100, 255),
    "green": (0, 200, 80),
    "yellow": (255, 220, 0),
    "white": (240, 240, 240),
    "grey": (120, 120, 120),
    "dark_grey": (40, 40, 45),
}
