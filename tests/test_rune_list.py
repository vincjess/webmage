"""RuneList behaviour, including the two defects carried in 1.0.3."""

from __future__ import annotations

import pytest

from webmage.rune_list import RuneList


class FakeRune:
    """Enough of a Rune for list-level behaviour, with no browser involved."""

    def __init__(self, tag: str, attrs: dict[str, str], text: str = "") -> None:
        self.tag_name = tag
        self._attrs = attrs
        self.text = text

    def __getitem__(self, key: str) -> str | None:
        return self._attrs.get(key)


@pytest.fixture
def runes() -> RuneList:
    return RuneList(
        [
            FakeRune("a", {"href": "/one"}, "One"),
            FakeRune("a", {"href": "/two"}, "Two"),
            FakeRune("a", {}, "Three"),
        ]
    )


def test_integer_index_returns_one_rune(runes: RuneList) -> None:
    assert runes[0].text == "One"


def test_string_index_collects_one_attribute_from_each(runes: RuneList) -> None:
    assert runes["href"] == ["/one", "/two", None]


def test_slicing_returns_a_rune_list(runes: RuneList) -> None:
    """1.0.3 matched neither branch for a slice and silently returned None."""
    sliced = runes[:2]
    assert isinstance(sliced, RuneList)
    assert len(sliced) == 2
    assert sliced["href"] == ["/one", "/two"]


def test_repr_does_not_raise(runes: RuneList) -> None:
    """1.0.3's __repr__ read `.name`, which Rune never defined."""
    assert repr(runes) == "RuneList([<a>, <a>, <a>])"


def test_str_lists_tags(runes: RuneList) -> None:
    assert str(runes) == "[<a>, <a>, <a>]"


def test_text_collects_every_text(runes: RuneList) -> None:
    assert runes.text == ["One", "Two", "Three"]


def test_is_a_real_list(runes: RuneList) -> None:
    assert len(runes) == 3
    assert [r.text for r in runes] == ["One", "Two", "Three"]
    assert isinstance(runes, list)


def test_empty_list_reprs_cleanly() -> None:
    assert repr(RuneList()) == "RuneList([])"
