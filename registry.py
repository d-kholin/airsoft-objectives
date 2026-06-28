import importlib
import pkgutil
import modes
from game_mode import GameMode


def discover_modes():
    result = []
    for _importer, modname, _ispkg in pkgutil.iter_modules(modes.__path__):
        mod = importlib.import_module(f"modes.{modname}")
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and issubclass(obj, GameMode) and obj is not GameMode:
                result.append(obj)
    return result
