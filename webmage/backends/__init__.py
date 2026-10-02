"""Backend registry.

Engines are imported lazily, so installing just one of Selenium or Playwright is
enough to use the library.
"""

from __future__ import annotations

from typing import Any

from ..exceptions import EngineNotAvailableError
from .base import Backend, ElementAdapter

__all__ = ["Backend", "ElementAdapter", "create_backend", "available_engines", "ENGINES"]

ENGINES = ("playwright", "selenium")


def _load(engine: str) -> type[Backend]:
    if engine == "selenium":
        from ._selenium import SeleniumBackend

        return SeleniumBackend
    from ._playwright import PlaywrightBackend

    return PlaywrightBackend


def available_engines() -> list[str]:
    """Engines whose driver package is importable right now."""
    found = []
    for engine in ENGINES:
        module = "playwright.sync_api" if engine == "playwright" else "selenium"
        try:
            __import__(module)
        except ImportError:
            continue
        found.append(engine)
    return found


def create_backend(engine: str = "auto", **kwargs: Any) -> Backend:
    """Build a backend.

    ``engine="auto"`` prefers Playwright, which ships its own browsers, and
    falls back to Selenium.
    """
    key = engine.strip().lower()

    if key == "auto":
        found = available_engines()
        if not found:
            raise EngineNotAvailableError(
                "Neither Playwright nor Selenium is installed. Install one with "
                "`pip install webmage[playwright]` or `pip install webmage[selenium]`."
            )
        key = found[0]

    if key not in ENGINES:
        raise EngineNotAvailableError(
            f"Unknown engine {engine!r}. Choose one of: {', '.join(ENGINES)}, or 'auto'."
        )
    return _load(key)(**kwargs)
