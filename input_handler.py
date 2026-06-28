import pygame


class InputHandler:
    def __init__(self, button_map):
        self.button_map = button_map

    def poll(self):
        actions = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append("QUIT")
            elif event.type == pygame.KEYDOWN:
                if event.key in self.button_map:
                    actions.append(self.button_map[event.key])
        return actions
