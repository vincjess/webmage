"""WebMage -- a small, readable wrapper around browser automation.

One API over two engines. Playwright drives Chromium, Firefox and WebKit and
installs its own browsers; Selenium drives Chrome, Firefox, Edge and Safari
through Selenium Manager. Scripts written against WebMage run on either::

    from webmage import WebMage

    with WebMage("https://example.com", headless=True) as spell:
        heading = spell.wait_for("h1")
        print(heading.text)
        print(spell.select_all("a")["href"])
"""

from __future__ import annotations

from .backends import ENGINES, available_engines
from .exceptions import (
    BrowserNotSupportedError,
    ElementNotFoundError,
    EngineNotAvailableError,
    JavaScriptError,
    WaitTimeoutError,
    WebMageError,
)
from .rune import Rune
from .rune_list import RuneList
from .spell import Spell

__version__ = "2.0.0"

__all__ = [
    "WebMage",
    "Spell",
    "Rune",
    "RuneList",
    "ENGINES",
    "available_engines",
    "WebMageError",
    "EngineNotAvailableError",
    "BrowserNotSupportedError",
    "ElementNotFoundError",
    "WaitTimeoutError",
    "JavaScriptError",
    "__version__",
]


def WebMage(
    url: str,
    *,
    engine: str = "auto",
    browser: str = "chrome",
    headless: bool = False,
    driver_path: str | None = None,
    capture_network: bool = False,
) -> Spell:
    """Open a browser at ``url`` and return a :class:`~webmage.spell.Spell`.

    :param engine: ``"playwright"``, ``"selenium"``, or ``"auto"`` to prefer
        whichever is installed (Playwright first).
    :param browser: ``chrome``/``chromium``, ``firefox``, ``webkit``/``safari``
        or ``edge``. Names are normalised per engine, so ``"chrome"`` works on
        both.
    :param headless: Run without a visible window.
    :param driver_path: Selenium only. An explicit driver binary; omit it and
        Selenium Manager finds one.
    :param capture_network: Record requests and responses for
        :meth:`~webmage.spell.Spell.get_network_log`. Off by default because it
        costs throughput.

    Prefer using it as a context manager so the browser always closes::

        with WebMage("https://example.com") as spell:
            ...
    """
    return Spell(
        url=url,
        engine=engine,
        browser=browser,
        headless=headless,
        driver_path=driver_path,
        capture_network=capture_network,
    )
