"""The browser session: WebMage's main entry point."""

from __future__ import annotations

import sys
from collections.abc import Callable
from time import sleep
from types import TracebackType
from typing import Any
from urllib.parse import urlparse

from .backends import Backend, create_backend
from .exceptions import ElementNotFoundError
from .rune import Rune
from .rune_list import RuneList

__all__ = ["Spell"]

# Reading scrollHeight and setting scrollTop both need to resolve the scrolling
# element first. The selector arrives as an argument rather than being pasted
# into the source, so a selector containing a quote cannot break the script.
_SCROLL_HEIGHT_JS = """
var el = arguments[0] ? document.querySelector(arguments[0]) : document.scrollingElement;
if (!el) { return null; }
return el.scrollHeight;
"""

_SCROLL_TO_JS = """
var el = arguments[0] ? document.querySelector(arguments[0]) : document.scrollingElement;
if (!el) { return null; }
el.scrollTop = arguments[1] === null ? el.scrollHeight : arguments[1];
return el.scrollHeight;
"""

ScrollCallback = Callable[["Spell"], Any]


class Spell:
    """A live browser session.

    Build one with :func:`webmage.WebMage` rather than directly::

        with WebMage("https://example.com", headless=True) as spell:
            print(spell.select("h1").text)

    Used as a context manager the browser always closes, including on an
    exception, which is the usual source of leaked browser processes.
    """

    def __init__(
        self,
        url: str,
        engine: str = "playwright",
        browser: str = "chromium",
        headless: bool = False,
        driver_path: str | None = None,
        capture_network: bool = False,
    ) -> None:
        self._backend: Backend = create_backend(
            engine,
            browser=browser,
            headless=headless,
            driver_path=driver_path,
            capture_network=capture_network,
        )
        # Resolved, not requested: with engine="auto" the caller still gets to
        # see which engine actually started.
        self.engine = self._backend.name
        self.browser = self._backend.browser  # type: ignore[attr-defined]
        self._backend.goto(url)

    # -- context manager --------------------------------------------------

    def __enter__(self) -> Spell:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<Spell {self.engine}/{self.browser} on {self.url}>"

    # -- page state -------------------------------------------------------

    @property
    def url(self) -> str:
        """The URL currently loaded."""
        return self._backend.current_url

    @property
    def title(self) -> str:
        return self._backend.title

    def get_page_source(self) -> str:
        return self._backend.page_source

    def get_slug(self) -> str:
        """The last path segment of the URL, without query or fragment.

        Parsed with :mod:`urllib.parse` rather than the stack of regexes 1.0.x
        used, which mangled URLs with no path or with a dot in the query.
        """
        path = urlparse(self.url).path.rstrip("/")
        return path.rsplit("/", 1)[-1] if path else ""

    def change_url(self, url: str, retries: int = 0, retry_delay: float = 3.0) -> None:
        """Navigate to ``url``, optionally retrying on failure.

        ``retries`` is a finite count. 1.0.x looped forever behind a bare
        ``except:``, which also swallowed ``KeyboardInterrupt``, so a site that
        was simply down could not be interrupted with Ctrl-C.
        """
        attempts = max(0, retries) + 1
        last: Exception | None = None
        for attempt in range(attempts):
            try:
                self._backend.goto(url)
                return
            except Exception as exc:  # noqa: BLE001 - re-raised below
                last = exc
                if attempt + 1 < attempts:
                    self.wait(retry_delay)
        assert last is not None
        raise last

    # -- selecting --------------------------------------------------------

    def select(self, css_selector: str) -> Rune | None:
        """First match, or ``None``."""
        found = self._backend.find(css_selector)
        return Rune(found) if found else None

    def select_all(self, css_selector: str) -> RuneList:
        """Every match, as a :class:`~webmage.rune_list.RuneList`."""
        return RuneList(Rune(e) for e in self._backend.find_all(css_selector))

    def require(self, css_selector: str) -> Rune:
        """Like :meth:`select` but raises when nothing matches."""
        found = self.select(css_selector)
        if found is None:
            raise ElementNotFoundError(f"Nothing matched {css_selector!r}.")
        return found

    def wait_for(
        self, css_selector: str, timeout: float = 10.0, state: str = "visible"
    ) -> Rune:
        """Block until an element is ``attached``, ``visible`` or ``hidden``.

        The reason to prefer this over :meth:`wait`: it returns as soon as the
        page is ready instead of always sleeping the full interval, and it fails
        loudly when the element never arrives.
        """
        return Rune(self._backend.wait_for(css_selector, timeout, state))

    # -- interaction ------------------------------------------------------

    def click(self, css_selector: str) -> None:
        self.require(css_selector).click()

    def click_all(self, css_selector: str, wait_interval: float = 0.25) -> None:
        """Click every match, pausing between clicks.

        1.0.x called ``.click()`` on the *list* returned by ``find_elements``,
        so this method raised ``AttributeError`` on every call and had never
        worked.
        """
        for rune in self.select_all(css_selector):
            rune.click()
            self.wait(wait_interval)

    def type(self, css_selector: str, text: str) -> None:
        self.require(css_selector).type(text)

    def clear(self, css_selector: str) -> None:
        self.require(css_selector).clear()

    def get_screenshot(self, css_selector: str) -> bytes:
        """PNG bytes of one element."""
        return self.require(css_selector).screenshot()

    # -- scripting --------------------------------------------------------

    def cast_js(self, script: str, *args: Any) -> Any:
        """Run JavaScript in the page.

        ``script`` is a function body; extra arguments arrive as
        ``arguments[0]``, ``arguments[1]`` and so on, and ``return`` hands a
        value back. Identical on both engines.
        """
        return self._backend.execute_js(script, *args)

    def destroy(self, css_selector: str) -> None:
        """Remove the first matching element from the page."""
        self.cast_js(
            "var el = document.querySelector(arguments[0]); if (el) { el.remove(); }",
            css_selector,
        )

    def destroy_all(self, css_selector: str) -> None:
        """Remove every matching element from the page."""
        self.cast_js(
            "document.querySelectorAll(arguments[0]).forEach(el => el.remove());",
            css_selector,
        )

    # -- scrolling --------------------------------------------------------

    def _scroll_height(self, selector: str | None) -> int:
        height = self.cast_js(_SCROLL_HEIGHT_JS, selector)
        if height is None:
            raise ElementNotFoundError(f"No scrolling element matched {selector!r}.")
        return int(height)

    def _scroll_loop(
        self,
        wait_interval: float,
        selector: str | None,
        callback: ScrollCallback | None,
        verbose: bool,
        max_scrolls: int | None,
        pixel_step: int | None,
    ) -> int:
        """The engine behind all four scroll methods.

        ``pixel_step`` of ``None`` jumps to the bottom each time; an integer
        advances by that many pixels. ``max_scrolls`` of ``None`` runs until the
        page stops growing.
        """
        count = 0
        offset = 0
        last_height = self._scroll_height(selector)

        while max_scrolls is None or count < max_scrolls:
            if pixel_step is None:
                target: int | None = None
            else:
                offset += pixel_step
                target = offset

            new_height = self.cast_js(_SCROLL_TO_JS, selector, target)
            self.wait(wait_interval)
            count += 1

            if verbose:
                print(f"\rScroll #{count} completed!", end="", file=sys.stderr)
            if callback:
                callback(self)

            new_height = self._scroll_height(selector)
            if pixel_step is None:
                # Jump-to-bottom mode: nothing new loaded means we are done.
                if new_height == last_height:
                    break
            elif offset >= new_height:
                break
            last_height = new_height

        if verbose and count:
            print("", file=sys.stderr)
        return count

    def scroll(
        self,
        wait_interval: float,
        scroll_count: int,
        selector: str | None = None,
        callback: ScrollCallback | None = None,
        verbose: bool = False,
    ) -> int:
        """Jump to the bottom up to ``scroll_count`` times.

        Stops early once the page stops growing. Returns the number of scrolls
        performed.
        """
        return self._scroll_loop(
            wait_interval, selector, callback, verbose, scroll_count, None
        )

    def scroll_by_pixels(
        self,
        wait_interval: float,
        scroll_count: int,
        pixels: int = 500,
        selector: str | None = None,
        callback: ScrollCallback | None = None,
        verbose: bool = False,
    ) -> int:
        """Advance ``pixels`` at a time, up to ``scroll_count`` times.

        Gentler than :meth:`scroll` for pages that only load content for
        viewports they believe a human has actually passed through.
        """
        return self._scroll_loop(
            wait_interval, selector, callback, verbose, scroll_count, pixels
        )

    def infinite_scroll(
        self,
        wait_interval: float,
        selector: str | None = None,
        callback: ScrollCallback | None = None,
        verbose: bool = False,
        max_scrolls: int | None = None,
    ) -> int:
        """Jump to the bottom until the page stops growing.

        ``max_scrolls`` is an optional ceiling; 1.0.x had none, so a page that
        kept appending content looped forever.
        """
        return self._scroll_loop(
            wait_interval, selector, callback, verbose, max_scrolls, None
        )

    def infinite_scroll_by_pixels(
        self,
        wait_interval: float,
        pixels: int = 500,
        selector: str | None = None,
        callback: ScrollCallback | None = None,
        verbose: bool = False,
        max_scrolls: int | None = None,
    ) -> int:
        """Advance ``pixels`` at a time until the bottom is reached."""
        return self._scroll_loop(
            wait_interval, selector, callback, verbose, max_scrolls, pixels
        )

    # -- tabs and frames --------------------------------------------------

    def open_tab(
        self,
        url: str,
        callback: Callable[[Spell, Any], Any] | None = None,
        payload: Any = None,
    ) -> Any:
        """Open ``url`` in a second tab, run ``callback``, then close it.

        The callback receives ``(spell, payload)`` and whatever it returns comes
        back from this method. The tab closes even if the callback raises.
        """
        self._backend.open_tab(url)
        try:
            if callback is not None:
                payload = callback(self, payload)
        finally:
            self._backend.close_tab()
        return payload

    def switch_frames(self, css_selector: str) -> None:
        """Route subsequent queries into the matching iframe."""
        self._backend.switch_to_frame(css_selector)

    def switch_to_default_content(self) -> None:
        """Route queries back to the top-level document."""
        self._backend.switch_to_default_content()

    # -- misc -------------------------------------------------------------

    def get_network_log(self) -> list[dict[str, Any]]:
        """Network activity since the last call.

        Requires ``capture_network=True`` at construction. Each entry is a dict
        with ``type``, ``url``, ``method``, ``status``, ``resource_type`` and
        ``headers`` -- the same shape from both engines, where 1.0.x returned
        raw Chrome DevTools messages.
        """
        return self._backend.network_log()

    def wait(self, seconds: float) -> None:
        """Sleep. Prefer :meth:`wait_for` when waiting on an element."""
        sleep(seconds)

    def close(self) -> None:
        """Shut the browser down."""
        self._backend.close()
