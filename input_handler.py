import pygame
from settings import KEY_MAP


class InputHandler:
    def __init__(self, button_map):
        self.button_map = button_map
        self._held = set()  # set of action strings currently held

    def is_action_held(self, action):
        return action in self._held

    def poll(self):
        actions = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append("QUIT")
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in self.button_map:
                    action = self.button_map[event.button]
                    self._held.add(action)
                    actions.append(action)
            elif event.type == pygame.JOYBUTTONUP:
                if event.button in self.button_map:
                    self._held.discard(self.button_map[event.button])
            elif event.type == pygame.KEYDOWN:
                if event.key in KEY_MAP:
                    action = KEY_MAP[event.key]
                    self._held.add(action)
                    actions.append(action)
            elif event.type == pygame.KEYUP:
                if event.key in KEY_MAP:
                    self._held.discard(KEY_MAP[event.key])
        return actions
