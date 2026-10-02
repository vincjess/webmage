"""A single element on the page."""

from __future__ import annotations

from typing import Any

from .backends.base import ElementAdapter
from .rune_list import RuneList

__all__ = ["Rune"]


class Rune:
    """One DOM element, independent of which engine found it.

    Every property reads through to the live element rather than caching at
    construction. 1.0.x snapshotted ``text``, ``outerHTML`` and ``tagName`` the
    moment a rune was built, so a rune held across a click or a scroll reported
    the old page.
    """

    __slots__ = ("_adapter",)

    def __init__(self, adapter: ElementAdapter) -> None:
        self._adapter = adapter

    # -- content ----------------------------------------------------------

    @property
    def text(self) -> str:
        """Rendered text content."""
        return self._adapter.text

    @property
    def tag_name(self) -> str:
        """Lowercased tag name, e.g. ``"a"``."""
        return self._adapter.tag_name

    @property
    def inner_html(self) -> str:
        return self._adapter.inner_html

    @property
    def outer_html(self) -> str:
        return self._adapter.outer_html

    @property
    def attributes(self) -> dict[str, str]:
        """Every attribute as a dict.

        A property, not a method: in 1.0.x ``getAttributes()`` had to be called
        before ``rune.attributes`` existed, so following the documented usage
        raised ``AttributeError``.
        """
        return self._adapter.attributes()

    def __getitem__(self, name: str) -> str | None:
        """Return an HTML attribute, or ``None`` when absent (never ``KeyError``).

        This is the literal attribute as written in the markup, so ``href`` on
        ``<a href="/one">`` is ``"/one"``, not the resolved absolute URL. For the
        live DOM property -- the current ``value`` of an input someone has typed
        into, or a resolved ``href`` -- use :meth:`get_property`.
        """
        return self._adapter.get_attribute(name)

    def get_property(self, name: str) -> Any:
        """Return a live JavaScript property of the element.

        ``rune["value"]`` is the ``value`` attribute from the markup;
        ``rune.get_property("value")`` is what the field currently holds.
        """
        return self._adapter.get_property(name)

    def __contains__(self, name: str) -> bool:
        return self._adapter.get_attribute(name) is not None

    # -- traversal --------------------------------------------------------

    def select(self, css_selector: str) -> Rune | None:
        """First descendant matching ``css_selector``, or ``None``."""
        found = self._adapter.find(css_selector)
        return Rune(found) if found else None

    def select_all(self, css_selector: str) -> RuneList:
        """Every descendant matching ``css_selector``."""
        return RuneList(Rune(e) for e in self._adapter.find_all(css_selector))

    # -- interaction ------------------------------------------------------

    def click(self) -> None:
        self._adapter.click()

    def clear(self) -> None:
        self._adapter.clear()

    def type(self, text: str) -> None:
        self._adapter.type(text)

    def screenshot(self) -> bytes:
        """PNG bytes of this element."""
        return self._adapter.screenshot()

    def cast_js(self, script: str, *args: Any) -> Any:
        """Run JavaScript with this element as ``arguments[0]``."""
        return self._adapter.execute_js(script, *args)

    # -- mutation ---------------------------------------------------------

    def destroy(self) -> None:
        """Remove this element from the page."""
        self._adapter.execute_js("arguments[0].remove();")

    def destroy_all(self, css_selector: str) -> None:
        """Remove every descendant matching ``css_selector``."""
        self._adapter.execute_js(
            "arguments[0].querySelectorAll(arguments[1]).forEach(el => el.remove());",
            css_selector,
        )

    def unwrap(self) -> Any:
        """The underlying Selenium or Playwright element."""
        return self._adapter.unwrap()  # type: ignore[attr-defined]

    def __repr__(self) -> str:
        return f"<Rune {self.outer_html}>"

    def __str__(self) -> str:
        return self.outer_html
