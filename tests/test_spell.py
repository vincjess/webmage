"""Spell logic that needs no browser, exercised through a stand-in backend."""

from __future__ import annotations

from typing import Any

import pytest

from webmage.backends.base import Backend, ElementAdapter
from webmage.exceptions import ElementNotFoundError
from webmage.spell import Spell


class FakeBackend(Backend):
    """A complete Backend implementation.

    Implementing every abstract method here is itself the check that the ABC is
    satisfiable: if a new abstract method appears without an implementation,
    instantiating this class fails and these tests go red.
    """

    name = "fake"
    browser = "fake"

    def __init__(self, fail_times: int = 0, **_: Any) -> None:
        self._url = "about:blank"
        self.visited: list[str] = []
        self.scripts: list[tuple[str, tuple[Any, ...]]] = []
        self._fail_times = fail_times

    @property
    def current_url(self) -> str:
        return self._url

    @property
    def title(self) -> str:
        return "fake"

    @property
    def page_source(self) -> str:
        return "<html></html>"

    def goto(self, url: str) -> None:
        self.visited.append(url)
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("navigation failed")
        self._url = url

    def find(self, css_selector: str) -> ElementAdapter | None:
        return None

    def find_all(self, css_selector: str) -> list[ElementAdapter]:
        return []

    def wait_for(self, css_selector: str, timeout: float, state: str) -> ElementAdapter:
        raise AssertionError("not needed")

    def execute_js(self, script: str, *args: Any) -> Any:
        self.scripts.append((script, args))
        return None

    def network_log(self) -> list[dict[str, Any]]:
        return []

    def open_tab(self, url: str) -> None:
        self.visited.append(url)

    def close_tab(self) -> None:
        pass

    def switch_to_frame(self, css_selector: str) -> None:
        pass

    def switch_to_default_content(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_spell(monkeypatch: pytest.MonkeyPatch):
    def build(
        url: str = "https://example.com/", fail_times: int = 0, **kwargs: Any
    ) -> Spell:
        backend = FakeBackend(**kwargs)
        monkeypatch.setattr("webmage.spell.create_backend", lambda *a, **k: backend)
        spell = Spell(url)
        # Arm the failures only after construction, so the initial navigation
        # that Spell.__init__ performs does not consume one.
        backend._fail_times = fail_times
        return spell

    return build


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://x.com/a/b/the-slug", "the-slug"),
        ("https://x.com/a/b/the-slug/", "the-slug"),
        ("https://x.com/the-slug?q=1&r=2", "the-slug"),
        ("https://x.com/the-slug#section", "the-slug"),
        ("https://x.com/the-slug/?q=1#frag", "the-slug"),
        ("https://x.com/file.tar.gz", "file.tar.gz"),
        # No path at all. The old regex found nothing to substitute and handed
        # back the entire URL.
        ("https://x.com", ""),
        ("https://x.com/", ""),
    ],
)
def test_get_slug(fake_spell, url: str, expected: str) -> None:
    assert fake_spell(url).get_slug() == expected


def test_require_raises_when_nothing_matches(fake_spell) -> None:
    with pytest.raises(ElementNotFoundError) as info:
        fake_spell().require("#nope")
    assert "#nope" in str(info.value)


def test_select_returns_none_rather_than_raising(fake_spell) -> None:
    assert fake_spell().select("#nope") is None


def test_change_url_retries_a_finite_number_of_times(fake_spell) -> None:
    spell = fake_spell(fail_times=2)
    spell.change_url("https://x.com/target", retries=3, retry_delay=0)
    assert spell.url == "https://x.com/target"


def test_change_url_gives_up_and_re_raises(fake_spell) -> None:
    """1.0.x looped forever behind a bare except, swallowing Ctrl-C."""
    spell = fake_spell(fail_times=99)
    with pytest.raises(RuntimeError):
        spell.change_url("https://x.com/target", retries=2, retry_delay=0)


def test_destroy_passes_the_selector_as_an_argument(fake_spell) -> None:
    """Interpolating it into JS source broke on any selector with a quote."""
    spell = fake_spell()
    tricky = '[data-label="it\'s here"]'
    spell.destroy(tricky)
    script, args = spell._backend.scripts[-1]
    assert tricky not in script
    assert args == (tricky,)


def test_destroy_all_passes_the_selector_as_an_argument(fake_spell) -> None:
    spell = fake_spell()
    spell.destroy_all(".x")
    script, args = spell._backend.scripts[-1]
    assert ".x" not in script
    assert args == (".x",)


def test_context_manager_closes_even_on_error(fake_spell) -> None:
    spell = fake_spell()
    with pytest.raises(ValueError), spell:
        raise ValueError("boom")
    assert getattr(spell._backend, "closed", False) is True


def test_engine_reports_the_resolved_backend(fake_spell) -> None:
    assert fake_spell().engine == "fake"
