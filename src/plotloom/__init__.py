"""Extraction-ready Plotloom backend contracts and application factory."""

from .config import PlotloomSettings
from .domain import *  # noqa: F403


def __getattr__(name: str):
    """Keep direct project persistence importable without the retained runtime."""

    if name == "SQLiteRepository":
        from .persistence import SQLiteRepository
        return SQLiteRepository
    if name == "create_app":
        from .api import create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["SQLiteRepository", "PlotloomSettings", "create_app"]
