"""Playwright backend.

Playwright downloads and pins its own browser builds, so there is no driver to
locate and no version skew between browser and driver -- the usual cause of a
scraper that worked last year and does not today. It also reaches WebKit, which
Selenium cannot drive outside macOS.

The one real impedance mismatch is script evaluation. Selenium's
``execute_script`` takes a *function body* that uses ``arguments[0]``; Playwright
takes an expression or an arrow function with a single parameter. Rather than
expose that difference, this backend wraps incoming scripts in a real (non-arrow)
function and ``apply``s the arguments to it, which rebinds ``arguments`` exactly
as Selenium would. The same script text therefore runs unchanged on either
engine.
"""

from __future__ import annotations

from typing import Any

from ..exceptions import (
    EngineNotAvailableError,
    JavaScriptError,
    WaitTimeoutError,
)
from .base import Backend, ElementAdapter

__all__ = ["PlaywrightBackend"]

_ALIASES = {
    "chrome": "chromium",
    "google-chrome": "chromium",
    "edge": "chromium",
    "safari": "webkit",
    "ff": "firefox",
}
_SUPPORTED = ("chromium", "firefox", "webkit")

_STATES = {
    "attached": "attached",
    "visible": "visible",
    "hidden": "hidden",
    "detached": "detached",
}


def _as_function_body(script: str) -> str:
    """Rebind ``arguments`` inside a plain function so Selenium scripts work."""
    return "(a) => (function(){ " + script + " }).apply(null, a)"


def _as_element_function_body(script: str) -> str:
    """Same, with the element supplied as ``arguments[0]``."""
    return "(e, a) => (function(){ " + script + " }).apply(null, [e].concat(a))"


def _unwrap(value: Any) -> Any:
    return value.unwrap() if isinstance(value, PlaywrightElement) else value


class PlaywrightElement(ElementAdapter):
    """Wraps a ``playwright.sync_api.ElementHandle``."""

    __slots__ = ("_el",)

    def __init__(self, element: Any) -> None:
        self._el = element

    @property
    def text(self) -> str:
        return self._el.inner_text()

    @property
    def tag_name(self) -> str:
        return self._el.evaluate("e => e.tagName.toLowerCase()")

    @property
    def inner_html(self) -> str:
        return self._el.inner_html()

    @property
    def outer_html(self) -> str:
        return self._el.evaluate("e => e.outerHTML")

    def get_attribute(self, name: str) -> str | None:
        return self._el.get_attribute(name)

    def get_property(self, name: str) -> Any:
        return self._el.evaluate("(e, n) => e[n]", name)

    def attributes(self) -> dict[str, str]:
        return self._el.evaluate(
            "e => Object.fromEntries([...e.attributes].map(a => [a.name, a.value]))"
        )

    def find(self, css_selector: str) -> ElementAdapter | None:
        found = self._el.query_selector(css_selector)
        return PlaywrightElement(found) if found else None

    def find_all(self, css_selector: str) -> list[ElementAdapter]:
        return [PlaywrightElement(e) for e in self._el.query_selector_all(css_selector)]

    def click(self) -> None:
        self._el.click()

    def clear(self) -> None:
        self._el.fill("")

    def type(self, text: str) -> None:
        self._el.type(text)

    def screenshot(self) -> bytes:
        return self._el.screenshot()

    def execute_js(self, script: str, *args: Any) -> Any:
        raw = [_unwrap(a) for a in args]
        try:
            return self._el.evaluate(_as_element_function_body(script), raw)
        except Exception as exc:  # Playwright raises its own Error subclass
            raise JavaScriptError(str(exc)) from exc

    def unwrap(self) -> Any:
        """The underlying Playwright handle, for callers who need to drop down."""
        return self._el


class PlaywrightBackend(Backend):
    name = "playwright"

    def __init__(
        self,
        browser: str = "chromium",
        headless: bool = False,
        capture_network: bool = False,
        **_: Any,
    ) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise EngineNotAvailableError(
                "The playwright engine needs Playwright. Install it with "
                "`pip install webmage[playwright]` then `playwright install`."
            ) from exc

        self.browser = self._normalise_browser(
            browser, _ALIASES, _SUPPORTED, "playwright"
        )
        self.headless = headless
        self._capture_network = capture_network
        self._network: list[dict[str, Any]] = []
        self._frame: Any = None

        self._pw = sync_playwright().start()
        try:
            self._browser = getattr(self._pw, self.browser).launch(headless=headless)
        except Exception:
            self._pw.stop()
            raise
        self._context = self._browser.new_context()
        self._pages = [self._context.new_page()]
        self._watch(self._pages[0])

    # -- internals --------------------------------------------------------

    @property
    def _page(self) -> Any:
        return self._pages[-1]

    def _target(self) -> Any:
        """Where queries run: the switched-to frame, else the active page."""
        return self._frame if self._frame is not None else self._page

    def _watch(self, page: Any) -> None:
        if not self._capture_network:
            return
        page.on("request", self._on_request)
        page.on("response", self._on_response)

    def _on_request(self, request: Any) -> None:
        self._network.append(
            {
                "type": "request",
                "url": request.url,
                "method": request.method,
                "status": None,
                "resource_type": request.resource_type,
                "headers": dict(request.headers),
            }
        )

    def _on_response(self, response: Any) -> None:
        self._network.append(
            {
                "type": "response",
                "url": response.url,
                "method": None,
                "status": response.status,
                "resource_type": None,
                "headers": dict(response.headers),
            }
        )

    # -- page state -------------------------------------------------------

    @property
    def current_url(self) -> str:
        return self._page.url

    @property
    def title(self) -> str:
        return self._page.title()

    @property
    def page_source(self) -> str:
        return self._page.content()

    def goto(self, url: str) -> None:
        self._frame = None
        self._page.goto(url)

    # -- querying ---------------------------------------------------------

    def find(self, css_selector: str) -> ElementAdapter | None:
        found = self._target().query_selector(css_selector)
        return PlaywrightElement(found) if found else None

    def find_all(self, css_selector: str) -> list[ElementAdapter]:
        return [
            PlaywrightElement(e) for e in self._target().query_selector_all(css_selector)
        ]

    def wait_for(self, css_selector: str, timeout: float, state: str) -> ElementAdapter:
        try:
            handle = self._target().wait_for_selector(
                css_selector, timeout=timeout * 1000, state=_STATES[state]
            )
        except Exception as exc:
            raise WaitTimeoutError(
                f"{css_selector!r} was not {state} after {timeout}s."
            ) from exc
        if handle is None:
            raise WaitTimeoutError(f"{css_selector!r} is gone from the DOM.")
        return PlaywrightElement(handle)

    # -- scripting --------------------------------------------------------

    def execute_js(self, script: str, *args: Any) -> Any:
        raw = [_unwrap(a) for a in args]
        try:
            return self._target().evaluate(_as_function_body(script), raw)
        except Exception as exc:
            raise JavaScriptError(str(exc)) from exc

    # -- network ----------------------------------------------------------

    def network_log(self) -> list[dict[str, Any]]:
        # Drained on read, matching the Selenium performance log's behaviour so
        # the two engines agree.
        entries, self._network = self._network, []
        return entries

    # -- tabs and frames --------------------------------------------------

    def open_tab(self, url: str) -> None:
        page = self._context.new_page()
        self._watch(page)
        self._pages.append(page)
        self._frame = None
        page.goto(url)

    def close_tab(self) -> None:
        if len(self._pages) == 1:
            return
        self._pages.pop().close()
        self._frame = None

    def switch_to_frame(self, css_selector: str) -> None:
        handle = self._page.query_selector(css_selector)
        if handle is None:
            from ..exceptions import ElementNotFoundError

            raise ElementNotFoundError(f"No frame matched {css_selector!r}.")
        self._frame = handle.content_frame()

    def switch_to_default_content(self) -> None:
        self._frame = None

    # -- teardown ---------------------------------------------------------

    def close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._pw.stop()
