from .logger import HaicLogger

try:
    from importlib.metadata import version as _v
    __version__ = _v("haic-logging")
except Exception:
    __version__ = "0.1.0"

__all__ = ["HaicLogger", "__version__"]
