import pygame

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
FPS = 30

# USB encoder board button-to-action mapping.
# Run `python3 -c "import pygame; pygame.init(); s=pygame.display.set_mode((200,200)); [print(e.key) for e in iter(lambda: pygame.event.wait(), None) if e.type==pygame.KEYDOWN]"`
# to discover your board's keycodes, then update this map.
BUTTON_MAP = {
    pygame.K_UP: "UP",
    pygame.K_DOWN: "DOWN",
    pygame.K_1: "RED_BUTTON",
    pygame.K_2: "BLUE_BUTTON",
    pygame.K_3: "GREEN_BUTTON",
    pygame.K_5: "START",
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
