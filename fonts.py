"""Centralized font loading.

Provides a cached monospace face so the terminal/digital readouts and tabular
layouts render with fixed-width glyphs that align by construction. Falls back
to pygame's bundled default if no system monospace font is found.
"""

import pygame
from functools import lru_cache

# Preference order; pygame.font.match_font picks the first that resolves.
_MONO_CHAIN = "dejavusansmono,liberationmono,freemono,consolas,couriernew,monospace"


@lru_cache(maxsize=1)
def _mono_path():
    try:
        return pygame.font.match_font(_MONO_CHAIN)
    except Exception:
        return None


@lru_cache(maxsize=None)
def get_font(size, mono=False):
    """Return a (cached) font at ``size``.

    With ``mono=True`` a fixed-width face is used when one is available.
    """
    if mono:
        path = _mono_path()
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def char_width(font):
    """Advance width of one glyph in a monospace font."""
    return font.size("0")[0]
