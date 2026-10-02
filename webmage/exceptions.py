"""Exception types raised by WebMage.

Every error WebMage raises inherits from :class:`WebMageError`, so callers can
catch the whole library with one ``except`` without also swallowing unrelated
failures from Selenium or Playwright.
"""

from __future__ import annotations

__all__ = [
    "WebMageError",
    "EngineNotAvailableError",
    "BrowserNotSupportedError",
    "ElementNotFoundError",
    "WaitTimeoutError",
    "JavaScriptError",
]


class WebMageError(Exception):
    """Base class for every error raised by WebMage."""


class EngineNotAvailableError(WebMageError):
    """A backend was requested whose driver package is not installed."""


class BrowserNotSupportedError(WebMageError):
    """A browser was requested that the chosen engine cannot drive."""


class ElementNotFoundError(WebMageError):
    """An element was required but no node matched the selector."""


class WaitTimeoutError(WebMageError):
    """An element did not reach the expected state before the timeout.

    Named to avoid shadowing the built-in :class:`TimeoutError`.
    """


class JavaScriptError(WebMageError):
    """Script evaluation failed in the page."""
