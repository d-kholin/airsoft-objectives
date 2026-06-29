import pygame
import math
import random
import time
from game_mode import GameMode
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT, BUTTON_MAP
from ui import draw_menu_item
from widgets import draw_7seg_time, seg7_width, handle_custom_timer, draw_custom_timer
from presets import timer_presets, COUNTDOWN_PRESETS, DISARM_PRESETS
from fonts import get_font

CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

GAME_PRESETS = timer_presets()
LAUNCH_PRESETS = COUNTDOWN_PRESETS

PREP_PHASES = ["FUEL", "ARM", "RAISE"]

DENIED_FLASH = 1.4

AMBER = (255, 176, 0)
DIM_AMBER = (160, 112, 0)
ALERT_RED = (255, 40, 40)
DIM_RED = (70, 8, 8)


def _telemetry_line():
    templates = [
        lambda: f"GUIDANCE {random.choice(['LOCKED','TRACKING','NOMINAL'])}  AZ {random.randint(0,359):03d}  EL {random.randint(0,89):02d}",
        lambda: f"SILO {random.randint(1,12):02d}  DOOR {random.choice(['OPEN','SEALED'])}  PRESS {random.uniform(0.8,1.2):.2f}ATM",
        lambda: f"FUEL {random.randint(82,100):3d}%  OX {random.randint(82,100):3d}%  THRUST {random.randint(0,100):3d}%",
        lambda: f"TGT {random.choice('ABCDEF')}{random.randint(10,99)}  RANGE {random.randint(1000,9999)}KM  CEP {random.randint(5,80)}m",
        lambda: f"WARHEAD {random.choice(['ARMED','SAFE'])}  SEQ {random.randint(1000,9999)}  CRC {random.choice(['OK','OK','OK','ERR'])}",
        lambda: f"INERTIAL {random.choice(['ALIGNED','SLEWING'])}  GYRO {random.uniform(-0.5,0.5):+.2f}  DRIFT {random.randint(0,9)}",
        lambda: f"UPLINK {random.choice(['SATCOM','HF','VLF'])}  KEY {random.choice(['VALID','VALID','HELD'])}  BIT {random.randint(0,9)}",
    ]
    return random.choice(templates)()


class MissileLaunchMode(GameMode):
    name = "Missile Launch"
    mode_id = "missile_launch"
    description = "Fuel, arm, and raise the missile — then enter launch codes before the enemy disables it"

    def setup(self, config=None):
        config = config or {}
        self.font_big = pygame.font.Font(None, 88)
        self.font_med = pygame.font.Font(None, 50)
        self.font_sm = pygame.font.Font(None, 34)
        self.font_mono = get_font(22, mono=True)
        self.font_label = get_font(26, mono=True)
        self.font_phase = pygame.font.Font(None, 42)

        self.game_total = 900
        self.countdown_total = 120
        self.hold_time = 15

        self.game_selection = 2
        self.countdown_selection = 1
        self.hold_selection = 2
        self.custom_minutes = 2

        self.game_remaining = 0.0

        # Prep phases: FUEL → ARM → RAISE
        self.prep_phase = 0          # 0-2 = working on this phase, 3 = all done
        self.phase_progress = 0.0    # 0..hold_time for current phase

        self.secret_chars = []
        self.secret_index = 0
        self.input_chars = []
        self.input_index = 0
        self.failed_attempts = 0
        self.denied_timer = 0.0

        self.timer_remaining = 0.0
        self.abort_progress = 0.0
        self.disable_progress = 0.0

        self.result = None
        self.time_left_at_end = 0
        self.play_start_time = 0

        self.blink = 0.0
        self.anim_time = 0.0
        self.pulse_time = 0.0
        self.launch_anim = 0.0
        self.telemetry = [_telemetry_line() for _ in range(11)]
        self.telemetry_timer = 0.0

        self.action_keys = {}
        for key, action in BUTTON_MAP.items():
            self.action_keys.setdefault(action, []).append(key)

        if "game_time" in config or "countdown" in config or "hold_time" in config:
            self.game_total = config.get("game_time", self.game_total)
            self.countdown_total = config.get("countdown", self.countdown_total)
            self.hold_time = config.get("hold_time", self.hold_time)
            code = self.app.config_store.get_launch_code()
            if code:
                self.secret_chars = list(code)
                self._enter_prep()
            else:
                self.phase = "setup_code"
        else:
            self.phase = "setup_game_time"

    def _is_held(self, action):
        pressed = pygame.key.get_pressed()
        return any(pressed[k] for k in self.action_keys.get(action, []))

    def _nav(self, selection, count, actions):
        if "UP" in actions:
            selection = (selection - 1) % count
        if "DOWN" in actions:
            selection = (selection + 1) % count
        confirm = "START" in actions or "GREEN_BUTTON" in actions
        return selection, confirm

    def _scroll(self, index, actions):
        if "UP" in actions:
            index = (index - 1) % len(CHARSET)
        if "DOWN" in actions:
            index = (index + 1) % len(CHARSET)
        return index

    def handle_input(self, actions):
        handler = {
            "setup_game_time": self._handle_game_time,
            "setup_game_custom": self._handle_game_custom,
            "setup_countdown": self._handle_countdown,
            "setup_countdown_custom": self._handle_countdown_custom,
            "setup_hold": self._handle_hold,
            "setup_code": self._handle_setup_code,
            "code_entry": self._handle_code_entry,
        }.get(self.phase)
        if handler:
            handler(actions)
        elif self.phase == "result":
            if "START" in actions or "GREEN_BUTTON" in actions:
                self.setup()

    def _handle_game_time(self, actions):
        self.game_selection, confirm = self._nav(self.game_selection, len(GAME_PRESETS), actions)
        if confirm:
            value = GAME_PRESETS[self.game_selection][1]
            if value is None:
                self.custom_minutes = self.game_total // 60
                self.phase = "setup_game_custom"
            else:
                self.game_total = value
                self.phase = "setup_countdown"

    def _handle_game_custom(self, actions):
        self.custom_minutes, result = handle_custom_timer(actions, self.custom_minutes)
        if result == "back":
            self.phase = "setup_game_time"
        elif result == "confirm":
            self.game_total = self.custom_minutes * 60
            self.phase = "setup_countdown"

    def _handle_countdown(self, actions):
        self.countdown_selection, confirm = self._nav(self.countdown_selection, len(LAUNCH_PRESETS), actions)
        if confirm:
            value = LAUNCH_PRESETS[self.countdown_selection][1]
            if value is None:
                self.custom_minutes = self.countdown_total // 60
                self.phase = "setup_countdown_custom"
            else:
                self.countdown_total = value
                self.phase = "setup_hold"

    def _handle_countdown_custom(self, actions):
        self.custom_minutes, result = handle_custom_timer(actions, self.custom_minutes)
        if result == "back":
            self.phase = "setup_countdown"
        elif result == "confirm":
            self.countdown_total = self.custom_minutes * 60
            self.phase = "setup_hold"

    def _handle_hold(self, actions):
        self.hold_selection, confirm = self._nav(self.hold_selection, len(DISARM_PRESETS), actions)
        if confirm:
            self.hold_time = DISARM_PRESETS[self.hold_selection][1]
            self.phase = "setup_code"

    def _handle_setup_code(self, actions):
        self.secret_index = self._scroll(self.secret_index, actions)
        if "GREEN_BUTTON" in actions:
            self.secret_chars.append(CHARSET[self.secret_index])
            self.secret_index = 0
            self.app.sound.play("confirm")
        if "RED_BUTTON" in actions and self.secret_chars:
            self.secret_chars.pop()
        if "START" in actions and self.secret_chars:
            self.app.sound.play("confirm")
            self._enter_prep()

    def _handle_code_entry(self, actions):
        self.input_index = self._scroll(self.input_index, actions)
        if "GREEN_BUTTON" in actions:
            self.input_chars.append(CHARSET[self.input_index])
            self.input_index = 0
            self.app.sound.play("confirm")
        if "RED_BUTTON" in actions and self.input_chars:
            self.input_chars.pop()
        if "START" in actions and self.input_chars:
            if "".join(self.input_chars) == "".join(self.secret_chars):
                self._begin_countdown()
            else:
                self.failed_attempts += 1
                self.denied_timer = DENIED_FLASH
                self.input_chars = []
                self.input_index = 0
                self.app.sound.play("error")

    def _enter_prep(self):
        self.phase = "prep"
        self.prep_phase = 0
        self.phase_progress = 0.0
        self.disable_progress = 0.0
        self.game_remaining = float(self.game_total)
        self.play_start_time = time.time()

    def _begin_countdown(self):
        self.phase = "countdown"
        self.timer_remaining = float(self.countdown_total)
        self.abort_progress = 0.0
        self.app.sound.play("confirm")

    # --- update ----------------------------------------------------------

    def update(self, dt):
        self.blink += dt
        self.anim_time += dt
        if self.denied_timer > 0:
            self.denied_timer = max(0.0, self.denied_timer - dt)

        self.telemetry_timer += dt
        if self.telemetry_timer > 0.35:
            self.telemetry_timer = 0.0
            self.telemetry.pop(0)
            self.telemetry.append(_telemetry_line())

        if self.phase in ("prep", "code_entry"):
            self.game_remaining -= dt
            if self.game_remaining <= 0:
                self.game_remaining = 0
                self._finish("TIMEOUT")
                return

        if self.phase == "prep":
            blue = self._is_held("BLUE_BUTTON")
            red = self._is_held("RED_BUTTON")

            if blue and not red:
                self.phase_progress += dt
                if self.phase_progress >= self.hold_time:
                    self.prep_phase += 1
                    self.phase_progress = 0.0
                    self.app.sound.play("confirm")
                    if self.prep_phase >= len(PREP_PHASES):
                        self.phase = "code_entry"
                        self.input_chars = []
                        self.input_index = 0

            if red and not blue:
                self.phase_progress -= dt
                if self.phase_progress < 0:
                    if self.prep_phase > 0:
                        self.prep_phase -= 1
                        self.phase_progress = self.hold_time
                    else:
                        self.phase_progress = 0.0
                        self.disable_progress += dt
                        if self.disable_progress >= self.hold_time:
                            self._finish("DISABLED")
                            return
                self.disable_progress = max(0.0, self.disable_progress - dt * 0.5)
            else:
                self.disable_progress = max(0.0, self.disable_progress - dt * 2)

        elif self.phase == "countdown":
            self.timer_remaining -= dt
            if self._is_held("RED_BUTTON"):
                self.abort_progress += dt
                if self.abort_progress >= self.hold_time:
                    self._finish("ABORTED")
                    return
            elif self.abort_progress > 0:
                self.abort_progress = max(0.0, self.abort_progress - dt * 2)
            if self.timer_remaining <= 0:
                self.timer_remaining = 0
                self._finish("LAUNCHED")

        elif self.phase == "result":
            self.pulse_time += dt
            if self.result == "LAUNCHED":
                self.launch_anim += dt

    def _finish(self, result):
        self.result = result
        self.time_left_at_end = max(0, int(self.game_remaining))
        self.phase = "result"
        self.pulse_time = 0.0
        self.launch_anim = 0.0
        self._save_history()
        if result == "LAUNCHED":
            self.app.sound.play("victory")
        else:
            self.app.sound.play("defeat")

    # --- drawing ---------------------------------------------------------

    def draw(self, screen):
        if self.phase == "setup_game_time":
            self._draw_choice(screen, "Set game time", GAME_PRESETS, self.game_selection)
        elif self.phase == "setup_game_custom":
            draw_custom_timer(screen, self.font_big, self.font_sm, "MISSILE LAUNCH",
                              self.custom_minutes, sub="Set custom game time (minutes)")
        elif self.phase == "setup_countdown":
            self._draw_choice(screen, "Set launch countdown", LAUNCH_PRESETS, self.countdown_selection)
        elif self.phase == "setup_countdown_custom":
            draw_custom_timer(screen, self.font_big, self.font_sm, "MISSILE LAUNCH",
                              self.custom_minutes, sub="Set custom countdown")
        elif self.phase == "setup_hold":
            self._draw_choice(screen, "Set hold time (per phase / abort)", DISARM_PRESETS, self.hold_selection)
        elif self.phase == "setup_code":
            self._draw_setup_code(screen)
        elif self.phase == "prep":
            self._draw_prep(screen)
        elif self.phase == "code_entry":
            self._draw_code_entry(screen)
        elif self.phase == "countdown":
            self._draw_countdown(screen)
        elif self.phase == "result":
            self._draw_result(screen)

    def _draw_grid(self, screen, color):
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(screen, color, (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))

    def _draw_char_entry(self, screen, chars, index, x, y, accent):
        cx = x
        char_h = self.font_med.get_height()
        if chars:
            confirmed = self.font_med.render("".join(chars), True, accent)
            screen.blit(confirmed, (cx, y))
            cx += confirmed.get_width() + 6
        box = pygame.Rect(cx, y, 34, char_h)
        pygame.draw.rect(screen, accent, box)
        curr = self.font_med.render(CHARSET[index], True, COLORS["bg"])
        screen.blit(curr, curr.get_rect(center=box.center))
        prev = self.font_sm.render(CHARSET[(index - 1) % len(CHARSET)], True, COLORS["grey"])
        screen.blit(prev, prev.get_rect(centerx=box.centerx, bottom=box.top - 4))
        nxt = self.font_sm.render(CHARSET[(index + 1) % len(CHARSET)], True, COLORS["grey"])
        screen.blit(nxt, nxt.get_rect(centerx=box.centerx, top=box.bottom + 4))

    def _draw_telemetry(self, screen, rect, color):
        screen.set_clip(rect)
        for i, line in enumerate(self.telemetry):
            c = color if i % 2 == 0 else tuple(max(0, v - 30) for v in color)
            surf = self.font_mono.render(line, True, c)
            screen.blit(surf, (rect.x, rect.y + i * 22))
        screen.set_clip(None)

    def _draw_choice(self, screen, sub, presets, selection):
        self._draw_grid(screen, (16, 12, 0))
        title = self.font_big.render("MISSILE LAUNCH", True, AMBER)
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=24))
        sub_surf = self.font_sm.render(sub, True, COLORS["white"])
        screen.blit(sub_surf, sub_surf.get_rect(centerx=SCREEN_WIDTH // 2, y=118))
        x = SCREEN_WIDTH // 2 - 130
        for i, (label, _) in enumerate(presets):
            draw_menu_item(screen, self.font_med, label, i == selection,
                           x, 168 + i * 52, accent=AMBER)
        hints = self.font_sm.render("UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 38))

    def _fmt(self, secs):
        return f"{int(secs) // 60}:{int(secs) % 60:02d}"

    def _draw_setup_code(self, screen):
        self._draw_grid(screen, (16, 12, 0))
        title = self.font_med.render("LAUNCH AUTHORIZATION", True, AMBER)
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=36))
        sub = self.font_sm.render(
            "GAME MASTER: set the secret launch code", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=98))
        label = self.font_label.render("LAUNCH CODE:", True, AMBER)
        screen.blit(label, (120, 230))
        self._draw_char_entry(screen, self.secret_chars, self.secret_index, 130, 280, AMBER)
        cfg = self.font_sm.render(
            f"Game {self._fmt(self.game_total)}   Countdown {self._fmt(self.countdown_total)}   "
            f"Hold {self.hold_time}s", True, COLORS["grey"])
        screen.blit(cfg, cfg.get_rect(centerx=SCREEN_WIDTH // 2, y=410))
        hints = self.font_sm.render(
            "UP/DOWN=char  GREEN=add  RED=delete  START=arm system", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 38))

    def _draw_missile(self, screen, cx, base_y, scale, flame, raised_pct=0.0):
        """Draw a missile. raised_pct 0-1 controls vertical offset (raised position)."""
        offset = int(raised_pct * 60 * scale)
        base_y -= offset
        bw = int(26 * scale)
        bh = int(120 * scale)
        nose = int(40 * scale)
        body = pygame.Rect(cx - bw // 2, base_y - bh, bw, bh)
        pygame.draw.rect(screen, (210, 210, 215), body)
        pygame.draw.rect(screen, (120, 120, 128), body, 2)
        tip = (cx, base_y - bh - nose)
        pygame.draw.polygon(screen, ALERT_RED, [
            (body.left, base_y - bh), (body.right, base_y - bh), tip])
        pygame.draw.rect(screen, (60, 120, 220),
                         (body.left, base_y - bh + int(18 * scale), bw, int(8 * scale)))
        fin = int(22 * scale)
        pygame.draw.polygon(screen, (150, 30, 30), [
            (body.left, base_y - fin), (body.left - fin, base_y), (body.left, base_y)])
        pygame.draw.polygon(screen, (150, 30, 30), [
            (body.right, base_y - fin), (body.right + fin, base_y), (body.right, base_y)])
        if flame > 0:
            flick = random.uniform(0.7, 1.3)
            fl = int(70 * scale * flame * flick)
            fw = int(bw * 0.8)
            pygame.draw.polygon(screen, AMBER, [
                (cx - fw // 2, base_y), (cx + fw // 2, base_y), (cx, base_y + fl)])
            pygame.draw.polygon(screen, ALERT_RED, [
                (cx - fw // 3, base_y), (cx + fw // 3, base_y), (cx, base_y + int(fl * 0.6))])

    def _draw_phase_indicators(self, screen, y):
        """Draw the three-phase checklist with progress bar for current phase."""
        cx = SCREEN_WIDTH // 2
        phase_w = 220
        gap = 30
        total = len(PREP_PHASES) * phase_w + (len(PREP_PHASES) - 1) * gap
        sx = cx - total // 2

        for i, name in enumerate(PREP_PHASES):
            x = sx + i * (phase_w + gap)
            bar_h = 32

            if i < self.prep_phase:
                # Completed
                pygame.draw.rect(screen, COLORS["green"], (x, y, phase_w, bar_h), border_radius=4)
                label = self.font_phase.render(f"[OK] {name}", True, COLORS["bg"])
            elif i == self.prep_phase:
                # In progress
                pct = self.phase_progress / self.hold_time if self.hold_time > 0 else 0
                pygame.draw.rect(screen, (30, 30, 40), (x, y, phase_w, bar_h), border_radius=4)
                fill = int(phase_w * pct)
                if fill > 0:
                    pygame.draw.rect(screen, AMBER, (x, y, fill, bar_h), border_radius=4)
                pygame.draw.rect(screen, AMBER, (x, y, phase_w, bar_h), 2, border_radius=4)
                secs_left = max(0, self.hold_time - self.phase_progress)
                label = self.font_phase.render(f"{name}  {int(secs_left)}s", True, COLORS["white"])
            else:
                # Locked
                pygame.draw.rect(screen, (25, 25, 30), (x, y, phase_w, bar_h), border_radius=4)
                pygame.draw.rect(screen, COLORS["grey"], (x, y, phase_w, bar_h), 1, border_radius=4)
                label = self.font_phase.render(name, True, COLORS["grey"])

            screen.blit(label, label.get_rect(center=(x + phase_w // 2, y + bar_h // 2)))

    def _draw_prep(self, screen):
        self._draw_grid(screen, (16, 12, 0))

        # Header
        pygame.draw.rect(screen, DIM_AMBER, (0, 0, SCREEN_WIDTH, 52))
        header = self.font_sm.render("STRATEGIC LAUNCH CONTROL  //  PREP SEQUENCE", True, AMBER)
        screen.blit(header, header.get_rect(centerx=SCREEN_WIDTH // 2, centery=26))

        # Game clock
        clock_col = ALERT_RED if self.game_remaining < 60 else AMBER
        clock = self.font_med.render(self._fmt(self.game_remaining), True, clock_col)
        screen.blit(clock, clock.get_rect(right=SCREEN_WIDTH - 16, y=62))
        gl = self.font_sm.render("GAME TIME", True, COLORS["grey"])
        screen.blit(gl, gl.get_rect(right=SCREEN_WIDTH - 16, y=104))

        # Current action
        phase_name = PREP_PHASES[self.prep_phase] if self.prep_phase < len(PREP_PHASES) else "READY"
        status = self.font_med.render(f"PHASE: {phase_name}", True, AMBER)
        screen.blit(status, (60, 72))

        # Phase indicators
        self._draw_phase_indicators(screen, 150)

        # Missile (evolves with phase completion)
        raised = 0.0
        if self.prep_phase >= 2:
            raised = self.phase_progress / self.hold_time if self.prep_phase == 2 else 1.0
        fuel_flame = 0.0
        if self.prep_phase >= 1:
            fuel_flame = 0.15 + 0.1 * math.sin(self.anim_time * 6)
        self._draw_missile(screen, 130, 460, 1.0, flame=fuel_flame, raised_pct=raised)

        # Telemetry
        self._draw_telemetry(screen, pygame.Rect(600, 210, 420, 230), DIM_AMBER)

        # Disable meter (shows when RED is held at phase 0 with 0 progress)
        if self.disable_progress > 0:
            pct = self.disable_progress / self.hold_time
            lbl = self.font_med.render(
                f"DISABLING {int(pct * 100)}%", True, ALERT_RED)
            screen.blit(lbl, lbl.get_rect(centerx=SCREEN_WIDTH // 2, y=470))
            bar_w, bar_h = 460, 24
            bx = SCREEN_WIDTH // 2 - bar_w // 2
            by = 512
            pygame.draw.rect(screen, (40, 10, 10), (bx, by, bar_w, bar_h))
            pygame.draw.rect(screen, ALERT_RED, (bx, by, int(bar_w * pct), bar_h))
            pygame.draw.rect(screen, ALERT_RED, (bx, by, bar_w, bar_h), 2)

        # Controls
        hint = self.font_sm.render(
            "HOLD [BLUE] to advance phase   //   HOLD [RED] to reverse / disable",
            True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 28))

    def _draw_code_entry(self, screen):
        self._draw_grid(screen, (16, 12, 0))
        pygame.draw.rect(screen, DIM_AMBER, (0, 0, SCREEN_WIDTH, 52))
        header = self.font_sm.render("STRATEGIC LAUNCH CONTROL  //  READY", True, AMBER)
        screen.blit(header, header.get_rect(centerx=SCREEN_WIDTH // 2, centery=26))

        # Game clock
        clock_col = ALERT_RED if self.game_remaining < 60 else AMBER
        clock = self.font_med.render(self._fmt(self.game_remaining), True, clock_col)
        screen.blit(clock, clock.get_rect(right=SCREEN_WIDTH - 16, y=62))
        gl = self.font_sm.render("GAME TIME", True, COLORS["grey"])
        screen.blit(gl, gl.get_rect(right=SCREEN_WIDTH - 16, y=104))

        # All phases complete
        self._draw_phase_indicators(screen, 150)

        # Status
        ready = self.font_med.render("MISSILE READY — ENTER LAUNCH CODE", True, COLORS["green"])
        screen.blit(ready, ready.get_rect(centerx=SCREEN_WIDTH // 2, y=210))

        # Code entry
        label = self.font_label.render("AUTH CODE:", True, AMBER)
        screen.blit(label, (120, 290))
        self._draw_char_entry(screen, self.input_chars, self.input_index, 130, 340, COLORS["green"])

        if self.denied_timer > 0 and int(self.denied_timer * 6) % 2 == 0:
            denied = self.font_med.render("ACCESS DENIED", True, ALERT_RED)
            screen.blit(denied, denied.get_rect(centerx=SCREEN_WIDTH // 2, y=430))
        elif int(self.blink * 2) % 2 == 0:
            wait = self.font_sm.render("> AWAITING INPUT_", True, COLORS["green"])
            screen.blit(wait, (130, 440))

        if self.failed_attempts:
            fa = self.font_sm.render(f"FAILED ATTEMPTS: {self.failed_attempts}", True, COLORS["grey"])
            screen.blit(fa, (130, 490))

        hint = self.font_sm.render(
            "UP/DOWN=char  GREEN=add  RED=delete  START=transmit", True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 38))

    def _draw_countdown(self, screen):
        alert = int(self.blink * 3) % 2 == 0
        self._draw_grid(screen, DIM_RED)

        banner_col = ALERT_RED if alert else (120, 20, 20)
        pygame.draw.rect(screen, (25, 0, 0), (0, 0, SCREEN_WIDTH, 56))
        banner = self.font_med.render("///  LAUNCH SEQUENCE INITIATED  ///", True, banner_col)
        screen.blit(banner, banner.get_rect(centerx=SCREEN_WIDTH // 2, centery=28))

        seg_w, seg_h, seg_t, seg_gap = 46, 84, 8, 8
        total_w = seg7_width(seg_w, seg_t, seg_gap)
        cx = SCREEN_WIDTH // 2 - total_w // 2
        seg_col = ALERT_RED if self.timer_remaining >= 10 or alert else AMBER
        draw_7seg_time(screen, cx, 92, self.timer_remaining, seg_col,
                       seg_w, seg_h, seg_t, seg_gap)
        tmin = self.font_sm.render("T-MINUS TO LAUNCH", True, COLORS["grey"])
        screen.blit(tmin, tmin.get_rect(centerx=SCREEN_WIDTH // 2, y=196))

        self._draw_missile(screen, 120, 470, 1.0,
                           flame=0.35 + 0.2 * math.sin(self.anim_time * 12),
                           raised_pct=1.0)
        self._draw_telemetry(screen, pygame.Rect(620, 226, 400, 200), DIM_AMBER)

        if self.abort_progress > 0:
            pct = self.abort_progress / self.hold_time
            lbl = self.font_med.render(
                f"ABORT SEQUENCE {int(pct * 100)}%  ({int(self.abort_progress)}/{self.hold_time}s)",
                True, COLORS["green"])
            screen.blit(lbl, lbl.get_rect(centerx=SCREEN_WIDTH // 2, y=462))
            bar_w, bar_h = 560, 30
            bx = SCREEN_WIDTH // 2 - bar_w // 2
            by = 512
            pygame.draw.rect(screen, (10, 40, 20), (bx, by, bar_w, bar_h))
            pygame.draw.rect(screen, COLORS["green"], (bx, by, int(bar_w * pct), bar_h))
            pygame.draw.rect(screen, COLORS["green"], (bx, by, bar_w, bar_h), 2)
        else:
            prompt_col = COLORS["green"] if alert else (0, 110, 45)
            prompt = self.font_med.render(
                f"HOLD  [RED]  {self.hold_time}s  TO ABORT", True, prompt_col)
            screen.blit(prompt, prompt.get_rect(centerx=SCREEN_WIDTH // 2, y=496))

        hint = self.font_sm.render(
            "Attackers: reach the box and hold RED to cancel the launch",
            True, COLORS["grey"])
        screen.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 28))

    def _draw_result(self, screen):
        if self.result == "LAUNCHED":
            self._draw_grid(screen, DIM_RED)
            rise = min(self.launch_anim * 220, SCREEN_HEIGHT + 200)
            base_y = SCREEN_HEIGHT + 40 - rise
            self._draw_missile(screen, SCREEN_WIDTH // 2, int(base_y), 1.4,
                               flame=1.0, raised_pct=1.0)
            if self.launch_anim < 0.4:
                flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                flash.fill(AMBER)
                flash.set_alpha(int(220 * (1 - self.launch_anim / 0.4)))
                screen.blit(flash, (0, 0))
            alpha = int((math.sin(self.pulse_time * 5) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in COLORS["green"])
            text = self.font_big.render("MISSILE LAUNCHED", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 120)))
            sub_text = "TARGET DESTROYED"
        elif self.result == "DISABLED":
            self._draw_grid(screen, DIM_RED)
            alpha = int((math.sin(self.pulse_time * 4) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in ALERT_RED)
            text = self.font_big.render("MISSILE DISABLED", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
            sub_text = "SYSTEM COMPROMISED"
        elif self.result == "ABORTED":
            self._draw_grid(screen, DIM_RED)
            alpha = int((math.sin(self.pulse_time * 4) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in ALERT_RED)
            text = self.font_big.render("LAUNCH ABORTED", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
            sub_text = "THREAT NEUTRALIZED"
        else:
            self._draw_grid(screen, (0, 30, 12))
            alpha = int((math.sin(self.pulse_time * 4) + 1) * 110)
            col = tuple(min(255, max(40, int(c * alpha / 255))) for c in ALERT_RED)
            text = self.font_big.render("TIME EXPIRED", True, col)
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)))
            sub_text = "LAUNCH PREVENTED"

        sub_surf = self.font_med.render(sub_text, True, col)
        sub_y = 190 if self.result == "LAUNCHED" else SCREEN_HEIGHT // 2
        screen.blit(sub_surf, sub_surf.get_rect(center=(SCREEN_WIDTH // 2, sub_y)))

        if self.result == "LAUNCHED":
            stat = f"Countdown: {self._fmt(self.countdown_total)}  |  Phases completed"
        elif self.result == "DISABLED":
            stat = f"Disabled at phase {self.prep_phase + 1}/{len(PREP_PHASES)}  |  {self._fmt(self.game_remaining)} left"
        elif self.result == "ABORTED":
            stat = f"Aborted with {self._fmt(self.time_left_at_end)} left on countdown"
        else:
            stat = f"Phases completed: {self.prep_phase}/{len(PREP_PHASES)}"
        stats = self.font_sm.render(
            f"{stat}  |  Failed codes: {self.failed_attempts}", True, COLORS["white"])
        screen.blit(stats, stats.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70)))

        prompt = self.font_sm.render("Press START to play again", True, COLORS["grey"])
        screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)))

    def _save_history(self):
        elapsed = time.time() - self.play_start_time if self.play_start_time else 0
        self.save_history({
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "result": self.result,
            "elapsed_seconds": round(elapsed),
            "failed_attempts": self.failed_attempts,
            "game_time": self.game_total,
            "countdown_total": self.countdown_total,
            "hold_time": self.hold_time,
            "phases_completed": self.prep_phase,
            "time_left": self.time_left_at_end,
        })
