"""A list of :class:`~webmage.rune.Rune` objects with scraping conveniences."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Any, SupportsIndex, overload

if TYPE_CHECKING:  # pragma: no cover
    from .rune import Rune

__all__ = ["RuneList"]


class RuneList(list):
    """A ``list`` of runes that can also be indexed by attribute name.

    Indexing by string pulls one attribute from every element at once, which is
    the common case when scraping::

        links = spell.select_all("a")
        urls = links["href"]        # ['/a', '/b', None, ...]
        labels = links.text         # ['Home', 'About', ...]
    """

    def __init__(self, iterable: Iterable[Rune] = ()) -> None:
        super().__init__(iterable)

    # Indexing by string widens list's contract on purpose, which no amount of
    # signature juggling can make LSP-clean.
    @overload  # type: ignore[override]
    def __getitem__(self, key: SupportsIndex) -> Rune: ...
    @overload
    def __getitem__(self, key: slice) -> RuneList: ...
    @overload
    def __getitem__(self, key: str) -> list[str | None]: ...

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            return [rune[key] for rune in self]
        if isinstance(key, slice):
            # 1.0.x fell through both branches here and silently returned None.
            return RuneList(super().__getitem__(key))
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[Rune]:  # pragma: no cover - typing only
        return super().__iter__()

    @property
    def text(self) -> list[str]:
        """The rendered text of every element."""
        return [rune.text for rune in self]

    def attributes(self) -> list[dict[str, str]]:
        """Every attribute of every element."""
        return [rune.attributes for rune in self]

    def _tags(self) -> str:
        # 1.0.x's __repr__ read `.name`, which Rune has never defined, so
        # repr() of a RuneList raised AttributeError.
        return ", ".join(f"<{rune.tag_name}>" for rune in self)

    def __repr__(self) -> str:
        return f"RuneList([{self._tags()}])"

    def __str__(self) -> str:
        return f"[{self._tags()}]"
