"""Shared on-device UI widgets used by more than one game mode."""

import pygame
from settings import COLORS, SCREEN_WIDTH, SCREEN_HEIGHT
from presets import CUSTOM_MIN_MINUTES, CUSTOM_MAX_MINUTES

_SEG_MAP = {
    0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg",
    4: "bcfg", 5: "acdfg", 6: "acdefg", 7: "abc",
    8: "abcdefg", 9: "abcdfg",
}


def _draw_7seg_digit(screen, x, y, digit, w, h, thick, color, dim_color):
    hh = h // 2
    t = thick
    seg_rects = {
        "a": (x + t, y, w - 2 * t, t),
        "b": (x + w - t, y + t, t, hh - t),
        "c": (x + w - t, y + hh, t, hh - t),
        "d": (x + t, y + h - t, w - 2 * t, t),
        "e": (x, y + hh, t, hh - t),
        "f": (x, y + t, t, hh - t),
        "g": (x + t, y + hh - t // 2, w - 2 * t, t),
    }
    active = _SEG_MAP.get(digit, "")
    for seg, rect in seg_rects.items():
        c = color if seg in active else dim_color
        pygame.draw.rect(screen, c, rect)


def draw_7seg_time(screen, cx, y, seconds, color, w=24, h=40, thick=4, gap=5):
    """Draw a MM:SS:hh seven-segment readout starting at (cx, y).

    ``color`` sets the lit-segment color; unlit segments are a dim derivative.
    """
    dim = tuple(max(c // 8, 6) for c in color)
    clamped = max(0.0, seconds)
    mins = int(clamped) // 60
    secs = int(clamped) % 60
    hundredths = int((clamped % 1) * 100)

    groups = [
        (mins // 10, mins % 10),
        (secs // 10, secs % 10),
        (hundredths // 10, hundredths % 10),
    ]
    for gi, (d1, d2) in enumerate(groups):
        _draw_7seg_digit(screen, cx, y, d1, w, h, thick, color, dim)
        cx += w + gap
        _draw_7seg_digit(screen, cx, y, d2, w, h, thick, color, dim)
        cx += w + gap
        if gi < 2:
            sep_sz = thick
            if gi == 0:
                pygame.draw.rect(screen, color, (cx, y + h // 3 - sep_sz // 2, sep_sz, sep_sz))
                pygame.draw.rect(screen, color, (cx, y + 2 * h // 3 - sep_sz // 2, sep_sz, sep_sz))
            else:
                pygame.draw.rect(screen, color, (cx, y + h - sep_sz, sep_sz, sep_sz))
            cx += sep_sz + gap


def seg7_width(w=24, thick=4, gap=5):
    """Pixel width of a MM:SS:hh readout for the given digit metrics."""
    return 6 * (w + gap) + 2 * (thick + gap)


def handle_custom_timer(actions, minutes):
    """Advance a custom-minutes selector.

    Returns ``(minutes, result)`` where result is "confirm", "back", or None.
    """
    if "UP" in actions:
        minutes = min(CUSTOM_MAX_MINUTES, minutes + 1)
    if "DOWN" in actions:
        minutes = max(CUSTOM_MIN_MINUTES, minutes - 1)
    if "RED_BUTTON" in actions:
        return minutes, "back"
    if "START" in actions or "GREEN_BUTTON" in actions:
        return minutes, "confirm"
    return minutes, None


def draw_custom_timer(screen, font_big, font_sm, title, minutes, sub="Set custom time"):
    """Draw the shared custom-timer entry screen."""
    title_surf = font_big.render(title, True, COLORS["yellow"])
    screen.blit(title_surf, title_surf.get_rect(centerx=SCREEN_WIDTH // 2, y=30))

    sub_surf = font_sm.render(sub, True, COLORS["white"])
    screen.blit(sub_surf, sub_surf.get_rect(centerx=SCREEN_WIDTH // 2, y=110))

    val = font_big.render(f"{minutes:02d}:00", True, COLORS["green"])
    screen.blit(val, val.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10)))

    label = font_sm.render("MINUTES", True, COLORS["grey"])
    screen.blit(label, label.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT // 2 + 50))

    hints = font_sm.render(
        "UP/DOWN=adjust  START/GREEN=confirm  RED=back", True, COLORS["grey"]
    )
    screen.blit(hints, hints.get_rect(centerx=SCREEN_WIDTH // 2, y=SCREEN_HEIGHT - 40))
