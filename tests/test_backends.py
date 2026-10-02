"""Engine registry and browser-name resolution. No browser is launched."""

from __future__ import annotations

import pytest

from webmage.backends import ENGINES, available_engines, create_backend
from webmage.backends._playwright import _as_element_function_body, _as_function_body
from webmage.backends.base import Backend
from webmage.exceptions import BrowserNotSupportedError, EngineNotAvailableError


def test_unknown_engine_names_the_valid_ones() -> None:
    with pytest.raises(EngineNotAvailableError) as info:
        create_backend("puppeteer")
    message = str(info.value)
    assert "puppeteer" in message
    for engine in ENGINES:
        assert engine in message


def test_available_engines_is_a_subset_of_known_engines() -> None:
    assert set(available_engines()) <= set(ENGINES)


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("chrome", "chrome"),
        ("CHROME", "chrome"),
        (" Chromium ", "chrome"),
        ("ff", "firefox"),
    ],
)
def test_selenium_browser_aliases_resolve(given: str, expected: str) -> None:
    from webmage.backends._selenium import _ALIASES, _SUPPORTED

    assert Backend._normalise_browser(given, _ALIASES, _SUPPORTED, "selenium") == expected


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("chrome", "chromium"),
        ("safari", "webkit"),
        ("edge", "chromium"),
        ("webkit", "webkit"),
    ],
)
def test_playwright_browser_aliases_resolve(given: str, expected: str) -> None:
    from webmage.backends._playwright import _ALIASES, _SUPPORTED

    assert (
        Backend._normalise_browser(given, _ALIASES, _SUPPORTED, "playwright") == expected
    )


def test_unsupported_browser_explains_the_alternatives() -> None:
    from webmage.backends._playwright import _ALIASES, _SUPPORTED

    with pytest.raises(BrowserNotSupportedError) as info:
        Backend._normalise_browser("netscape", _ALIASES, _SUPPORTED, "playwright")
    assert "netscape" in str(info.value)
    assert "chromium" in str(info.value)


def test_script_wrapper_rebinds_arguments() -> None:
    """The shim must produce a real function, so `arguments` is bound."""
    wrapped = _as_function_body("return arguments[0] + 1;")
    assert "function()" in wrapped
    assert ".apply(null, a)" in wrapped
    assert "return arguments[0] + 1;" in wrapped


def test_element_script_wrapper_puts_the_element_first() -> None:
    wrapped = _as_element_function_body("return arguments[0].tagName;")
    assert "[e].concat(a)" in wrapped
