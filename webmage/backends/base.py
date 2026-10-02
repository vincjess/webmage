"""The contract every browser backend implements.

WebMage's public objects (:class:`~webmage.spell.Spell`,
:class:`~webmage.rune.Rune`) hold a backend and never touch Selenium or
Playwright directly. Adding an engine means implementing these two classes and
registering it in :mod:`webmage.backends`; nothing else in the library changes.

Two deliberate normalisations keep the engines interchangeable:

* ``find``/``find_all`` return ``None``/``[]`` rather than raising, because
  Selenium raises ``NoSuchElementException`` where Playwright returns ``None``.
* ``get_attribute`` returns the literal HTML attribute on both engines, and
  ``get_property`` the live JavaScript property. Selenium's own
  ``get_attribute`` quietly prefers the property, so ``rune["value"]`` reported
  the typed-in text there and the original markup under Playwright.
* ``execute_js`` takes a *function body* using ``arguments[0]``, the Selenium
  convention the library has always documented. The Playwright backend wraps it
  so the same script text runs unchanged on both.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

__all__ = ["Backend", "ElementAdapter"]


class ElementAdapter(ABC):
    """A single DOM element, as the backend sees it.

    Values are read on demand rather than cached at construction: a scraped page
    mutates under you, and a stale ``text`` captured seconds earlier is worse
    than a slightly slower property.
    """

    @property
    @abstractmethod
    def text(self) -> str:
        """Rendered text content."""

    @property
    @abstractmethod
    def tag_name(self) -> str:
        """Lowercased tag name, e.g. ``"div"``."""

    @property
    @abstractmethod
    def inner_html(self) -> str: ...

    @property
    @abstractmethod
    def outer_html(self) -> str: ...

    @abstractmethod
    def get_attribute(self, name: str) -> str | None:
        """Return an attribute's value, or ``None`` when absent."""

    @abstractmethod
    def get_property(self, name: str) -> Any:
        """Return a live JavaScript property, e.g. the current ``value``."""

    @abstractmethod
    def attributes(self) -> dict[str, str]:
        """Every attribute on the element as a plain dict."""

    @abstractmethod
    def find(self, css_selector: str) -> ElementAdapter | None: ...

    @abstractmethod
    def find_all(self, css_selector: str) -> list[ElementAdapter]: ...

    @abstractmethod
    def click(self) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def type(self, text: str) -> None: ...

    @abstractmethod
    def screenshot(self) -> bytes:
        """PNG bytes of just this element."""

    @abstractmethod
    def execute_js(self, script: str, *args: Any) -> Any:
        """Run ``script`` with this element as ``arguments[0]``."""


class Backend(ABC):
    """A browser session."""

    #: Short engine name, e.g. ``"selenium"``.
    name: str

    @property
    @abstractmethod
    def current_url(self) -> str: ...

    @property
    @abstractmethod
    def title(self) -> str: ...

    @property
    @abstractmethod
    def page_source(self) -> str: ...

    @abstractmethod
    def goto(self, url: str) -> None: ...

    @abstractmethod
    def find(self, css_selector: str) -> ElementAdapter | None: ...

    @abstractmethod
    def find_all(self, css_selector: str) -> list[ElementAdapter]: ...

    @abstractmethod
    def wait_for(self, css_selector: str, timeout: float, state: str) -> ElementAdapter:
        """Block until an element reaches ``state``, then return it.

        ``state`` is one of ``"attached"``, ``"visible"`` or ``"hidden"``.
        Raises :class:`~webmage.exceptions.WaitTimeoutError` on expiry.
        """

    @abstractmethod
    def execute_js(self, script: str, *args: Any) -> Any:
        """Run a function body; ``args`` arrive as ``arguments[0]``, ``[1]``…"""

    @abstractmethod
    def network_log(self) -> list[dict[str, Any]]:
        """Network activity since the last call, in a normalised shape."""

    @abstractmethod
    def open_tab(self, url: str) -> None: ...

    @abstractmethod
    def close_tab(self) -> None: ...

    @abstractmethod
    def switch_to_frame(self, css_selector: str) -> None: ...

    @abstractmethod
    def switch_to_default_content(self) -> None: ...

    @abstractmethod
    def close(self) -> None:
        """Tear the session down completely, leaving no stray processes."""

    @staticmethod
    def _normalise_browser(
        browser: str, aliases: dict[str, str], supported: Sequence[str], engine: str
    ) -> str:
        """Resolve a user-supplied browser name for one engine."""
        from ..exceptions import BrowserNotSupportedError

        key = browser.strip().lower()
        key = aliases.get(key, key)
        if key not in supported:
            raise BrowserNotSupportedError(
                f"{engine} cannot drive {browser!r}. "
                f"Supported: {', '.join(sorted(supported))}."
            )
        return key
