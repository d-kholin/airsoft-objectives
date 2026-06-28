import pygame
from display import Display
from input_handler import InputHandler
from sound import SoundManager
from menu import MenuMode
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BUTTON_MAP, COLORS


class App:
    def __init__(self, fullscreen=True):
        pygame.init()
        self.display = Display(SCREEN_WIDTH, SCREEN_HEIGHT, fullscreen)
        self.input = InputHandler(BUTTON_MAP)
        self.sound = SoundManager()
        self.clock = pygame.time.Clock()
        self.running = True
        self.confirm_exit = False
        self.active_mode = None
        self.switch_mode(MenuMode)

    def switch_mode(self, mode_class, config=None):
        if self.active_mode:
            self.active_mode.teardown()
        self.active_mode = mode_class(self)
        self.active_mode.setup(config or {})

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            actions = self.input.poll()

            if "QUIT" in actions:
                self.running = False
                continue

            if "BACK" in actions and not isinstance(self.active_mode, MenuMode):
                if self.confirm_exit:
                    self.confirm_exit = False
                    self.switch_mode(MenuMode)
                else:
                    self.confirm_exit = True
                continue

            if self.confirm_exit and any(a for a in actions if a != "BACK"):
                self.confirm_exit = False

            self.active_mode.handle_input(actions)
            self.active_mode.update(dt)
            self.display.clear()
            self.active_mode.draw(self.display.screen)
            if self.confirm_exit:
                self._draw_exit_confirm(self.display.screen)
            self.display.flip()

        pygame.quit()

    def _draw_exit_confirm(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        font_big = pygame.font.Font(None, 60)
        font_sm = pygame.font.Font(None, 36)
        msg = font_big.render("EXIT TO MENU?", True, COLORS["yellow"])
        screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        hint = font_sm.render("BACK again = yes  /  any other key = cancel", True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)))
