import pygame
import math
import random
import time
from game_mode import GameMode
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT
from ui import draw_menu_item
from widgets import draw_7seg_time, handle_custom_timer, draw_custom_timer
from presets import timer_presets

GOAL_PRESETS = timer_presets()

CAPTURE_TIME = 10.0
CAPTURE_GRACE = 1.0

BATTLE_GROUND_Y = 448
GRAVITY = 650.0

COLOR_RED = (255, 40, 40)
COLOR_BLUE = (40, 100, 255)
DIM_RED = (80, 15, 15)
DIM_BLUE = (15, 30, 80)


class DominationMode(GameMode):
    name = "Domination"
    mode_id = "domination"
    description = "Two teams fight to hold the objective — first to the goal wins"

    def setup(self, config=None):
        config = config or {}
        self.font_big = pygame.font.Font(None, 80)
        self.font_med = pygame.font.Font(None, 52)
        self.font_sm = pygame.font.Font(None, 36)
        self.font_mono = pygame.font.Font(None, 28)
        self.goal_selection = 0
        self.custom_minutes = 10
        self.goal_time = 0
        self.red_time = 0.0
        self.blue_time = 0.0
        self.owner = None
        self.capture_progress = 0.0
        self.capturing_team = None
        self.capture_held_time = 0.0
        self.result = None
        self.pulse_time = 0.0
        self.play_start_time = 0
        self.play_end_time = 0
        self.anim_time = 0.0
        self.soldiers = self._init_soldiers()
        self.projectiles = []


        if "goal_time" in config:
            self.goal_time = config["goal_time"]
            self.phase = "play"
            self.play_start_time = time.time()
        else:
            self.phase = "setup"

    def _is_held(self, action):
        return self.app.input.is_action_held(action)

    def _init_soldiers(self):
        soldiers = []
        for i in range(4):
            x = 55 + i * 30
            soldiers.append({
                "team": "RED", "idx": i, "x": float(x), "home_x": float(x),
                "state": "idle", "frame": i * 0.4, "death_timer": 0.0,
                "shoot_cd": random.uniform(0.5, 1.5), "flash": 0.0,
            })
        for i in range(4):
            x = SCREEN_WIDTH - 55 - i * 30
            soldiers.append({
                "team": "BLUE", "idx": i, "x": float(x), "home_x": float(x),
                "state": "idle", "frame": i * 0.4, "death_timer": 0.0,
                "shoot_cd": random.uniform(0.5, 1.5), "flash": 0.0,
            })
        return soldiers

    def handle_input(self, actions):
        if self.phase == "setup":
            self._handle_setup(actions)
        elif self.phase == "setup_custom":
            self._handle_setup_custom(actions)
        elif self.phase == "play":
            self._handle_play(actions)
        elif self.phase == "result":
            if "START" in actions or "GREEN_BUTTON" in actions:
                self.setup()

    def _handle_setup(self, actions):
        if "UP" in actions:
            self.goal_selection = (self.goal_selection - 1) % len(GOAL_PRESETS)
        if "DOWN" in actions:
            self.goal_selection = (self.goal_selection + 1) % len(GOAL_PRESETS)
        if "START" in actions or "GREEN_BUTTON" in actions:
            preset = GOAL_PRESETS[self.goal_selection][1]
            if preset is None:
                self.phase = "setup_custom"
            else:
                self._start_play(preset)

    def _handle_setup_custom(self, actions):
        self.custom_minutes, result = handle_custom_timer(actions, self.custom_minutes)
        if result == "back":
            self.phase = "setup"
        elif result == "confirm":
            self._start_play(self.custom_minutes * 60)

    def _start_play(self, goal_seconds):
        self.goal_time = goal_seconds
        self.phase = "play"
        self.play_start_time = time.time()

    def _handle_play(self, actions):
        # Capture is driven by held-button state in update(), not single taps.
        pass

    def _update_capture(self, dt):
        # A team captures only while it holds its button. Release lets the
        # meter retreat at the same rate; if it drains to zero the attempt is
        # abandoned and the point reverts to neutral (or its prior owner).
        red_held = self._is_held("RED_BUTTON")
        blue_held = self._is_held("BLUE_BUTTON")

        if self.capturing_team is None:
            if red_held and self.owner != "RED":
                self.capturing_team = "RED"
                self.capture_progress = 0.0
                self.capture_held_time = 0.0
            elif blue_held and self.owner != "BLUE":
                self.capturing_team = "BLUE"
                self.capture_progress = 0.0
                self.capture_held_time = 0.0

        if self.capturing_team is None:
            return

        holding = red_held if self.capturing_team == "RED" else blue_held
        if holding:
            self.capture_held_time += dt
            self.capture_progress += dt
            if self.capture_progress >= CAPTURE_TIME:
                self.owner = self.capturing_team
                self.capturing_team = None
                self.capture_progress = 0.0
                self.app.sound.play("confirm")
        elif self.capture_held_time < CAPTURE_GRACE:
            # A quick accidental bump under the grace period cancels the
            # attempt outright without putting the current owner at risk.
            self.capturing_team = None
            self.capture_progress = 0.0
            self.capture_held_time = 0.0
        else:
            self.capture_progress -= dt
            if self.capture_progress <= 0:
                self.capture_progress = 0.0
                self.capturing_team = None
                # An abandoned capture leaves the point neutral — the previous
                # owner no longer holds it and stops scoring.
                self.owner = None

    def update(self, dt):
        if self.phase == "play":
            self._update_capture(dt)

            if self.capturing_team:
                pass
            elif self.owner == "RED":
                self.red_time += dt
            elif self.owner == "BLUE":
                self.blue_time += dt

            if self.red_time >= self.goal_time:
                self.result = "RED"
                self.phase = "result"
                self.pulse_time = 0.0
                self._save_history()
                self.app.sound.play("victory")
            elif self.blue_time >= self.goal_time:
                self.result = "BLUE"
                self.phase = "result"
                self.pulse_time = 0.0
                self._save_history()
                self.app.sound.play("victory")

        if self.phase in ("play", "result"):
            self.anim_time += dt
            self._update_soldiers(dt)
        if self.phase == "result":
            self.pulse_time += dt

    def draw(self, screen):
        if self.phase == "setup":
            self._draw_setup(screen)
        elif self.phase == "setup_custom":
            self._draw_setup_custom(screen)
        elif self.phase == "play":
            self._draw_play(screen)
        elif self.phase == "result":
            self._draw_result(screen)

    def _nearest_charger(self, enemy_team, near_x):
        chargers = [s for s in self.soldiers
                    if s["team"] == enemy_team and s["state"] == "charging"]
        if not chargers:
            return None
        return min(chargers, key=lambda s: abs(s["x"] - near_x))

    def _spawn_projectile(self, shooter, target, ground, facing):
        px = shooter["x"] + facing * 22
        py = ground - 30
        tx = target["x"]
        ty = ground - 8
        flight = 0.65
        vx = (tx - px) / flight
        vy = (ty - py - 0.5 * GRAVITY * flight * flight) / flight
        color = COLOR_RED if shooter["team"] == "RED" else COLOR_BLUE
        self.projectiles.append({
            "x": px, "y": py, "vx": vx, "vy": vy,
            "team": shooter["team"], "color": color,
        })

    def _update_soldiers(self, dt):
        mid = SCREEN_WIDTH // 2
        ground = BATTLE_GROUND_Y
        owner = self.owner
        capturing = self.capturing_team

        # The team taking/holding the point is the aggressor that shoots; the
        # other team charges in and gets killed. During the capture window the
        # capturing team is the aggressor, pushing in to take the defenders'
        # place. Once captured, the owner holds the firing line.
        aggressor = capturing if capturing else owner
        line_base = 40 if capturing else 75

        for s in self.soldiers:
            s["frame"] += dt
            if s["flash"] > 0:
                s["flash"] -= dt

            if s["state"] == "dead":
                s["death_timer"] -= dt
                if s["death_timer"] <= 0:
                    s["state"] = "idle"
                    s["x"] = s["home_x"]
                continue

            team = s["team"]
            idx = s["idx"]
            facing = 1 if team == "RED" else -1

            if aggressor is None:
                s["state"] = "idle"
                s["x"] += (s["home_x"] - s["x"]) * 3 * dt
                continue

            if team == aggressor:
                # Aggressor: form a firing line and shoot the chargers.
                s["state"] = "firing"
                tgt = (mid - line_base - idx * 28) if team == "RED" else (mid + line_base + idx * 28)
                s["x"] += max(-55 * dt, min(55 * dt, tgt - s["x"]))
                s["shoot_cd"] -= dt
                if s["shoot_cd"] <= 0:
                    enemy = "BLUE" if team == "RED" else "RED"
                    target = self._nearest_charger(enemy, mid)
                    if target is not None:
                        self._spawn_projectile(s, target, ground, facing)
                        s["flash"] = 0.1
                        s["shoot_cd"] = random.uniform(0.9, 1.7)
                    else:
                        s["shoot_cd"] = 0.4
            else:
                # Defenders being overrun: charge the point, die, respawn, repeat.
                s["state"] = "charging"
                s["x"] += facing * 70 * dt
                overran = (team == "RED" and s["x"] >= mid - 18) or \
                          (team == "BLUE" and s["x"] <= mid + 18)
                if overran:
                    s["state"] = "dead"
                    s["death_timer"] = random.uniform(1.6, 2.6)

        self._update_projectiles(dt, ground)

    def _update_projectiles(self, dt, ground):
        survivors = []
        for p in self.projectiles:
            p["vy"] += GRAVITY * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            landed = p["y"] >= ground - 6
            offscreen = p["x"] < -20 or p["x"] > SCREEN_WIDTH + 20
            if landed:
                enemy = "BLUE" if p["team"] == "RED" else "RED"
                victims = [s for s in self.soldiers
                           if s["team"] == enemy and s["state"] == "charging"
                           and abs(s["x"] - p["x"]) < 24]
                if victims:
                    v = min(victims, key=lambda s: abs(s["x"] - p["x"]))
                    v["state"] = "dead"
                    v["death_timer"] = random.uniform(1.6, 2.6)
            if not landed and not offscreen:
                survivors.append(p)
        self.projectiles = survivors

    def _draw_soldier(self, screen, sx, ground, facing, color, dark, state, frame, flash):
        x = int(sx)
        g = int(ground)

        if state == "dead":
            pygame.draw.line(screen, dark, (x - 11, g - 2), (x + 11, g - 1), 5)
            pygame.draw.circle(screen, color, (x - facing * 13, g - 4), 5)
            pygame.draw.circle(screen, dark, (x - facing * 13, g - 4), 5, 1)
            pygame.draw.line(screen, (40, 40, 40), (x + 2, g - 1), (x + facing * 13, g - 5), 2)
            return

        hip_y = g - 16
        shoulder_y = g - 30
        head_y = g - 38

        # Legs
        if state == "charging":
            sw = math.sin(frame * 13) * 7
        elif state == "advancing":
            sw = math.sin(frame * 9) * 5
        else:
            sw = 0
        pygame.draw.line(screen, dark, (x, hip_y), (x - 5 + int(sw), g), 4)
        pygame.draw.line(screen, dark, (x, hip_y), (x + 5 - int(sw), g), 4)

        # Torso
        pygame.draw.line(screen, color, (x, shoulder_y), (x, hip_y + 1), 7)

        # Head
        pygame.draw.circle(screen, color, (x, head_y), 6)
        pygame.draw.circle(screen, dark, (x, head_y), 6, 1)
        # Helmet
        pygame.draw.arc(screen, dark, (x - 8, head_y - 9, 16, 16), 0.15, math.pi - 0.15, 3)
        pygame.draw.line(screen, dark, (x - 7, head_y - 2),
                         (x + facing * 9, head_y - 2), 2)

        # Arms + rifle
        if state in ("firing", "idle"):
            grip = (x + facing * 10, shoulder_y + 3)
            tip = (x + facing * 23, shoulder_y + 1)
            stock = (x - facing * 4, shoulder_y + 6)
            pygame.draw.line(screen, color, (x, shoulder_y + 2), grip, 3)
            pygame.draw.line(screen, (35, 35, 40), stock, tip, 3)
            if flash > 0:
                fx, fy = int(tip[0] + facing * 3), int(tip[1])
                pygame.draw.circle(screen, COLORS["yellow"], (fx, fy), 5)
                pygame.draw.circle(screen, (255, 170, 50), (fx, fy), 8, 2)
        else:  # charging — rifle held across, arms pumping
            arm = math.sin(frame * 13) * 4
            pygame.draw.line(screen, color, (x, shoulder_y + 2),
                             (x + facing * 8, shoulder_y + 8 + int(arm)), 3)
            pygame.draw.line(screen, (35, 35, 40),
                             (x - facing * 2, shoulder_y + 10),
                             (x + facing * 14, shoulder_y + 4), 3)

    def _draw_battle(self, screen, ground):
        pygame.draw.line(screen, (45, 42, 32), (0, ground), (SCREEN_WIDTH, ground), 2)
        for s in self.soldiers:
            if s["team"] == "RED":
                color, dark, facing = COLOR_RED, (150, 20, 20), 1
            else:
                color, dark, facing = COLOR_BLUE, (20, 50, 140), -1
            self._draw_soldier(screen, s["x"], ground, facing, color, dark,
                               s["state"], s["frame"], s["flash"])
        for p in self.projectiles:
            px, py = int(p["x"]), int(p["y"])
            pygame.draw.circle(screen, p["color"], (px, py), 3)
            pygame.draw.circle(screen, (15, 15, 15), (px, py), 3, 1)

    def _draw_setup(self, screen):
        title = self.font_big.render("DOMINATION", True, COLORS["yellow"])
        screen.blit(title, title.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

        sub = self.font_sm.render("Set hold time goal", True, COLORS["white"])
        screen.blit(sub, sub.get_rect(centerx=SCREEN_WIDTH // 2, y=110))

        col_x = [200, 560]
        row_h = 55
        top = 150
        per_col = (len(GOAL_PRESETS) + 1) // 2
        for i, (label, _) in enumerate(GOAL_PRESETS):
            x = col_x[i // per_col]
            y = top + (i % per_col) * row_h
            draw_menu_item(screen, self.font_med, label, i == self.goal_selection, x, y)

        hints = self.font_sm.render("UP/DOWN=select  START/GREEN=confirm", True, COLORS["grey"])
        screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))

    def _draw_setup_custom(self, screen):
        draw_custom_timer(
            screen, self.font_big, self.font_sm, "DOMINATION",
            self.custom_minutes, sub="Set custom hold time",
        )

    def _draw_play(self, screen):
        mid = SCREEN_WIDTH // 2
        qtr = mid // 2

        # Background halves
        pygame.draw.rect(screen, DIM_RED, (0, 0, mid, SCREEN_HEIGHT))
        pygame.draw.rect(screen, DIM_BLUE, (mid, 0, mid, SCREEN_HEIGHT))
        pygame.draw.rect(screen, COLORS["white"], (mid - 2, 0, 4, SCREEN_HEIGHT))

        # Status banner at top (above team sections)
        banner_y = 10
        if self.capturing_team:
            cap_color = COLOR_RED if self.capturing_team == "RED" else COLOR_BLUE
            status = self.font_med.render(f"{self.capturing_team} CAPTURING...", True, cap_color)
        elif self.owner:
            owner_color = COLOR_RED if self.owner == "RED" else COLOR_BLUE
            status = self.font_med.render(f"{self.owner} HOLDS THE POINT", True, owner_color)
        else:
            status = self.font_med.render("POINT NEUTRAL", True, COLORS["grey"])
        # Draw on left or right side based on who it is, or centered if neutral
        if self.capturing_team == "RED" or (not self.capturing_team and self.owner == "RED"):
            screen.blit(status, status.get_rect(centerx=qtr, y=banner_y))
        elif self.capturing_team == "BLUE" or (not self.capturing_team and self.owner == "BLUE"):
            screen.blit(status, status.get_rect(centerx=mid + qtr, y=banner_y))
        else:
            screen.blit(status, status.get_rect(centerx=qtr, y=banner_y))
            status2 = self.font_med.render("POINT NEUTRAL", True, COLORS["grey"])
            screen.blit(status2, status2.get_rect(centerx=mid + qtr, y=banner_y))

        # Team labels
        red_label = self.font_big.render("RED", True, COLOR_RED)
        screen.blit(red_label, red_label.get_rect(centerx=qtr, y=60))
        blue_label = self.font_big.render("BLUE", True, COLOR_BLUE)
        screen.blit(blue_label, blue_label.get_rect(centerx=mid + qtr, y=60))

        # 7-segment timers
        timer_y = 145
        seg_w, seg_h, seg_t, seg_gap = 20, 36, 4, 4
        timer_pixel_w = 6 * (seg_w + seg_gap) + 2 * (seg_t + seg_gap)

        red_timer_x = qtr - timer_pixel_w // 2
        draw_7seg_time(screen, red_timer_x, timer_y, self.red_time, COLOR_RED, seg_w, seg_h, seg_t, seg_gap)

        blue_timer_x = mid + qtr - timer_pixel_w // 2
        draw_7seg_time(screen, blue_timer_x, timer_y, self.blue_time, COLOR_BLUE, seg_w, seg_h, seg_t, seg_gap)

        # Goal progress bars
        bar_y = 200
        goal_label = self.font_mono.render(f"Goal: {self.goal_time // 60}m", True, COLORS["white"])
        screen.blit(goal_label, goal_label.get_rect(centerx=qtr, y=bar_y))
        screen.blit(goal_label, goal_label.get_rect(centerx=mid + qtr, y=bar_y))

        bar_w = mid - 80
        bar_h = 18
        bar_y2 = bar_y + 25

        pygame.draw.rect(screen, (40, 10, 10), (40, bar_y2, bar_w, bar_h))
        red_fill = int(bar_w * min(self.red_time / self.goal_time, 1.0))
        if red_fill > 0:
            pygame.draw.rect(screen, COLOR_RED, (40, bar_y2, red_fill, bar_h))
        pygame.draw.rect(screen, COLOR_RED, (40, bar_y2, bar_w, bar_h), 2)

        bx = mid + 40
        pygame.draw.rect(screen, (10, 10, 40), (bx, bar_y2, bar_w, bar_h))
        blue_fill = int(bar_w * min(self.blue_time / self.goal_time, 1.0))
        if blue_fill > 0:
            pygame.draw.rect(screen, COLOR_BLUE, (bx, bar_y2, blue_fill, bar_h))
        pygame.draw.rect(screen, COLOR_BLUE, (bx, bar_y2, bar_w, bar_h), 2)

        # Battle scene
        self._draw_battle(screen, BATTLE_GROUND_Y)

        # Capture progress bar (centered in the capturing team's half)
        if self.capturing_team:
            cap_color = COLOR_RED if self.capturing_team == "RED" else COLOR_BLUE
            if self.capturing_team == "RED":
                cap_cx = qtr
            else:
                cap_cx = mid + qtr

            cap_bar_w = mid - 80
            cap_bar_x = cap_cx - cap_bar_w // 2
            cap_bar_y = 310

            cap_label = self.font_sm.render("CAPTURING", True, cap_color)
            screen.blit(cap_label, cap_label.get_rect(centerx=cap_cx, y=cap_bar_y - 30))

            pygame.draw.rect(screen, (30, 30, 35), (cap_bar_x, cap_bar_y, cap_bar_w, 25))
            cap_fill = int(cap_bar_w * min(self.capture_progress / CAPTURE_TIME, 1.0))
            if cap_fill > 0:
                pygame.draw.rect(screen, cap_color, (cap_bar_x, cap_bar_y, cap_fill, 25))
            pygame.draw.rect(screen, cap_color, (cap_bar_x, cap_bar_y, cap_bar_w, 25), 2)

            pct = int(self.capture_progress / CAPTURE_TIME * 100)
            pct_surf = self.font_sm.render(f"{pct}%", True, COLORS["white"])
            screen.blit(pct_surf, pct_surf.get_rect(centerx=cap_cx, y=cap_bar_y + 30))

        # Controls hint
        hint = self.font_mono.render(
            "HOLD RED button to capture for RED    HOLD BLUE button for BLUE",
            True, COLORS["grey"],
        )
        screen.blit(hint, hint.get_rect(centerx=mid, y=SCREEN_HEIGHT - 25))

    def _draw_result(self, screen):
        alpha = int((math.sin(self.pulse_time * 4) + 1) * 127)

        if self.result == "RED":
            text = "RED TEAM WINS"
            base_color = COLOR_RED
        else:
            text = "BLUE TEAM WINS"
            base_color = COLOR_BLUE

        color = tuple(min(255, max(40, int(c * alpha / 255))) for c in base_color)
        surf = self.font_big.render(text, True, color)
        screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))

        elapsed = self.play_end_time - self.play_start_time
        red_m, red_s = int(self.red_time) // 60, int(self.red_time) % 60
        blue_m, blue_s = int(self.blue_time) // 60, int(self.blue_time) % 60
        stats = self.font_sm.render(
            f"RED {red_m}:{red_s:02d}  |  BLUE {blue_m}:{blue_s:02d}  |  Game: {int(elapsed)//60}m{int(elapsed)%60:02d}s",
            True, COLORS["white"],
        )
        screen.blit(stats, stats.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)))

        prompt = self.font_sm.render("Press START to play again", True, COLORS["grey"])
        screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70)))

    def _save_history(self):
        self.play_end_time = time.time()
        elapsed = self.play_end_time - self.play_start_time
        self.save_history({
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "result": self.result,
            "elapsed_seconds": round(elapsed),
            "red_hold_time": round(self.red_time),
            "blue_hold_time": round(self.blue_time),
            "goal_time": self.goal_time,
        })
