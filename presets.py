"""Canonical setting presets shared by the on-device setup screens and the
web registry, so the two can never drift out of sync.

Kept free of any pygame import so the Flask web server can use it cheaply.
"""

# (label, seconds). The CUSTOM sentinel carries None for its value.
TIMER_PRESETS = [
    ("5 MIN", 300),
    ("10 MIN", 600),
    ("15 MIN", 900),
    ("20 MIN", 1200),
    ("25 MIN", 1500),
    ("30 MIN", 1800),
    ("CUSTOM", None),
]

MODULE_PRESETS = [
    ("3 MODULES", 3),
    ("4 MODULES", 4),
    ("5 MODULES", 5),
    ("6 MODULES", 6),
]

CUSTOM_MIN_MINUTES = 1
CUSTOM_MAX_MINUTES = 99


def timer_presets(include_off=False):
    """The timer presets as (label, seconds) tuples, optionally with OFF."""
    if include_off:
        return [("OFF", 0)] + list(TIMER_PRESETS)
    return list(TIMER_PRESETS)


def registry_options(presets):
    """Convert (label, value) preset tuples to the web registry's option dicts.

    The web UI represents CUSTOM with the sentinel value -1, so a preset value
    of None is mapped to -1 here.
    """
    return [
        {"label": label, "value": -1 if value is None else value}
        for label, value in presets
    ]
