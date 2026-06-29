import pygame
from pathlib import Path
from display import Display
from input_handler import InputHandler
from sound import SoundManager
from config_store import ConfigStore
from game_controller import GameController
from menu import MenuMode
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BUTTON_MAP, COLORS

SCREENSHOT_FILE = Path(__file__).parent / "data" / "screen.jpg"


class App:
    def __init__(self, fullscreen=True):
        pygame.init()
        self.display = Display(SCREEN_WIDTH, SCREEN_HEIGHT, fullscreen)
        self.input = InputHandler(BUTTON_MAP)
        self.sound = SoundManager()
        self.config_store = ConfigStore()
        self.game_controller = GameController()
        self.clock = pygame.time.Clock()
        self.running = True
        self.confirm_exit = False
        self.active_mode = None
        self.force_start_queued = False
        self.switch_mode(MenuMode)

    def switch_mode(self, mode_class, config=None):
        if self.active_mode:
            self.active_mode.teardown()
        self.active_mode = mode_class(self)
        self.active_mode.setup(config or {})

    def run(self):
        self._state_tick = 0
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            actions = self.input.poll()

            self._check_queued_commands()
            self._state_tick += 1
            if self._state_tick >= FPS:
                self._state_tick = 0
                self._update_game_state()
                self._save_screenshot()

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

    def _check_queued_commands(self):
        cmd = self.game_controller.get_command()
        if not cmd:
            return

        mode_id = cmd.get("mode")
        settings = cmd.get("settings", {})
        force = cmd.get("force", False)

        if mode_id == "__kill__":
            self.switch_mode(MenuMode)
            self.confirm_exit = False
            return

        from game_registry import get_mode_class
        mode_class = get_mode_class(mode_id)
        if not mode_class:
            return

        if force or isinstance(self.active_mode, MenuMode):
            self.switch_mode(mode_class, settings)
        else:
            self.force_start_queued = True

    def _update_game_state(self):
        mode = self.active_mode
        if isinstance(mode, MenuMode):
            state = {"status": "idle", "mode": None, "time_remaining": 0, "message": "Menu"}
        else:
            time_remaining = 0
            if hasattr(mode, "timer_remaining"):
                time_remaining = int(mode.timer_remaining)
            phase = getattr(mode, "phase", "unknown")
            if phase == "result":
                status = "finished"
            elif phase in ("play", "decrypting", "countdown"):
                status = "running"
            else:
                status = "setup"
            state = {
                "status": status,
                "mode": mode.name,
                "time_remaining": time_remaining,
                "message": phase,
            }
        self.game_controller.set_state(state)

    def _save_screenshot(self):
        try:
            SCREENSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.display.screen, str(SCREENSHOT_FILE))
        except Exception:
            pass

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
