"""End-to-end tests against a real browser.

Every test here runs once per installed engine, which is the point: the suite is
what proves Playwright and Selenium actually behave the same through WebMage's
API, rather than merely having similar-looking code.
"""

from __future__ import annotations

import pytest

from webmage.exceptions import ElementNotFoundError, WaitTimeoutError
from webmage.rune import Rune
from webmage.rune_list import RuneList

pytestmark = pytest.mark.browser


# -- page state -----------------------------------------------------------


def test_reports_title_and_url(open_page) -> None:
    spell = open_page()
    assert spell.title == "WebMage Test Page"
    assert spell.url.endswith("/index.html")


def test_page_source_contains_markup(open_page) -> None:
    assert "Hello WebMage" in open_page().get_page_source()


def test_get_slug_from_a_live_url(open_page) -> None:
    assert open_page().get_slug() == "index.html"


def test_engine_and_browser_are_reported(open_page) -> None:
    spell = open_page()
    assert spell.engine in ("playwright", "selenium")
    assert spell.browser


# -- selecting ------------------------------------------------------------


def test_select_returns_a_rune(open_page) -> None:
    heading = open_page().select("#title")
    assert isinstance(heading, Rune)
    assert heading.text == "Hello WebMage"
    assert heading.tag_name == "h1"


def test_select_returns_none_when_absent(open_page) -> None:
    assert open_page().select("#does-not-exist") is None


def test_require_raises_when_absent(open_page) -> None:
    with pytest.raises(ElementNotFoundError):
        open_page().require("#does-not-exist")


def test_select_all_returns_a_rune_list(open_page) -> None:
    links = open_page().select_all("nav a")
    assert isinstance(links, RuneList)
    assert len(links) == 3
    assert links.text == ["One", "Two", "Three"]


def test_rune_list_indexed_by_attribute(open_page) -> None:
    links = open_page().select_all("nav a")
    assert links["data-kind"] == ["internal", "internal", "external"]


def test_attribute_access_and_membership(open_page) -> None:
    link = open_page().select("nav a")
    assert link["data-kind"] == "internal"
    assert link["nope"] is None  # never a KeyError
    assert "data-kind" in link
    assert "nope" not in link


def test_attributes_is_a_property_not_a_method(open_page) -> None:
    """1.0.x required calling getAttributes() first; the docs said otherwise."""
    attrs = open_page().select("#quoted").attributes
    assert attrs["id"] == "quoted"
    assert attrs["data-label"] == "it's here"


def test_nested_selection_from_a_rune(open_page) -> None:
    items = open_page().select("#items")
    assert items.select(".item").text == "Alpha"
    assert items.select_all(".item")["data-id"] == ["1", "2", "3"]


def test_inner_and_outer_html(open_page) -> None:
    heading = open_page().select("#title")
    assert heading.inner_html == "Hello WebMage"
    assert heading.outer_html.startswith("<h1")


# -- waiting --------------------------------------------------------------


def test_wait_for_returns_once_the_element_arrives(open_page) -> None:
    late = open_page().wait_for("#late", timeout=5)
    assert late.text == "arrived"


def test_wait_for_times_out_loudly(open_page) -> None:
    with pytest.raises(WaitTimeoutError):
        open_page().wait_for("#never-appears", timeout=0.5)


# -- interaction ----------------------------------------------------------


def test_click_runs_the_handler(open_page) -> None:
    spell = open_page()
    spell.click(".tally")
    assert spell.select("#log").text == "a"


def test_click_all_clicks_every_match(open_page) -> None:
    """The headline regression: click_all raised AttributeError in 1.0.x."""
    spell = open_page()
    spell.click_all(".tally", wait_interval=0)
    assert spell.select("#log").text == "abc"


def test_type_and_clear(open_page) -> None:
    spell = open_page()
    assert spell.select("#name").get_property("value") == "preset"
    spell.clear("#name")
    spell.type("#name", "hello")
    assert spell.select("#name").get_property("value") == "hello"


def test_attribute_is_the_markup_property_is_live(open_page) -> None:
    """The two must not be conflated, and must agree across engines.

    Selenium's get_attribute silently prefers the JS property, so before this
    was normalised the same call returned the typed text on Selenium and the
    original markup on Playwright.
    """
    spell = open_page()
    spell.clear("#name")
    spell.type("#name", "typed")
    field = spell.select("#name")
    assert field["value"] == "preset"  # as written in the HTML
    assert field.get_property("value") == "typed"  # as it stands now


def test_href_is_the_literal_attribute_on_every_engine(open_page) -> None:
    """Selenium would otherwise resolve these to absolute URLs."""
    links = open_page().select_all("nav a")
    assert links["href"] == ["/one", "/two", "https://example.com"]


def test_get_property_resolves_href(open_page) -> None:
    link = open_page().select("nav a")
    assert link.get_property("href").endswith("/one")


def test_rune_text_is_read_live_not_cached(open_page) -> None:
    """1.0.x snapshotted text at construction, so this rune would read ''."""
    spell = open_page()
    log = spell.select("#log")
    assert log.text == ""
    spell.click(".tally")
    assert log.text == "a"


def test_element_screenshot_returns_png_bytes(open_page) -> None:
    data = open_page().get_screenshot("#pixel")
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


# -- scripting ------------------------------------------------------------


def test_cast_js_returns_a_value(open_page) -> None:
    assert open_page().cast_js("return 6 * 7;") == 42


def test_cast_js_receives_arguments(open_page) -> None:
    """Identical script text on both engines, via the arguments[0] shim."""
    spell = open_page()
    assert spell.cast_js("return arguments[0] + arguments[1];", 2, 3) == 5
    assert spell.cast_js("return arguments[0].toUpperCase();", "abc") == "ABC"


def test_cast_js_reads_the_dom(open_page) -> None:
    assert (
        open_page().cast_js(
            "return document.querySelectorAll(arguments[0]).length;", ".item"
        )
        == 3
    )


def test_rune_cast_js_gets_the_element_first(open_page) -> None:
    rune = open_page().select("#title")
    assert rune.cast_js("return arguments[0].tagName;") == "H1"
    assert rune.cast_js("return arguments[0].id + arguments[1];", "!") == "title!"


# -- mutation -------------------------------------------------------------


def test_destroy_removes_one_element(open_page) -> None:
    spell = open_page()
    assert spell.select("#doomed") is not None
    spell.destroy("#doomed")
    assert spell.select("#doomed") is None


def test_destroy_all_removes_every_match(open_page) -> None:
    spell = open_page()
    assert len(spell.select_all(".gone")) == 3
    spell.destroy_all(".gone")
    assert len(spell.select_all(".gone")) == 0


def test_destroy_handles_a_selector_containing_a_quote(open_page) -> None:
    """Pasting this selector into JS source produced a syntax error in 1.0.x."""
    spell = open_page()
    selector = '[data-label="it\'s here"]'
    assert spell.select(selector) is not None
    spell.destroy(selector)
    assert spell.select(selector) is None


def test_destroy_missing_element_is_a_no_op(open_page) -> None:
    open_page().destroy("#not-there")  # must not raise


def test_rune_destroy_removes_itself(open_page) -> None:
    spell = open_page()
    spell.select("#doomed").destroy()
    assert spell.select("#doomed") is None


# -- scrolling ------------------------------------------------------------


def test_scroll_moves_the_page(open_page) -> None:
    spell = open_page("scroll.html")
    performed = spell.scroll(0.15, 3)
    assert performed >= 1
    assert spell.cast_js("return document.scrollingElement.scrollTop;") > 0


def test_infinite_scroll_stops_when_growth_stops(open_page) -> None:
    spell = open_page("scroll.html")
    performed = spell.infinite_scroll(0.15, max_scrolls=12)
    assert 1 <= performed <= 12


def test_scroll_targets_a_custom_element(open_page) -> None:
    spell = open_page("scroll.html")
    spell.scroll_by_pixels(0.05, 3, pixels=200, selector="#box")
    assert spell.cast_js("return document.querySelector('#box').scrollTop;") > 0


def test_scroll_callback_runs_each_time(open_page) -> None:
    spell = open_page("scroll.html")
    seen: list[str] = []
    spell.scroll(0.05, 2, callback=lambda s: seen.append(s.url))
    assert len(seen) >= 1


def test_scrolling_an_absent_element_raises(open_page) -> None:
    with pytest.raises(ElementNotFoundError):
        open_page("scroll.html").scroll(0.05, 1, selector="#no-such-box")


# -- frames and tabs ------------------------------------------------------


def test_switch_into_and_out_of_a_frame(open_page) -> None:
    spell = open_page()
    spell.switch_frames("#frame")
    assert spell.select("#inside").text == "inside the frame"
    spell.switch_to_default_content()
    assert spell.select("#title") is not None


def test_open_tab_runs_callback_and_returns_payload(open_page, server) -> None:
    spell = open_page()
    original = spell.url

    def read_it(s, payload):
        return s.select("#inside").text

    result = spell.open_tab(f"{server}/inner.html", callback=read_it)
    assert result == "inside the frame"
    assert spell.url == original


# -- network --------------------------------------------------------------


def test_network_log_records_requests(open_page) -> None:
    spell = open_page()
    entries = spell.get_network_log()
    assert entries, "expected at least one network entry"
    assert {"type", "url", "method", "status", "resource_type", "headers"} <= set(
        entries[0]
    )
    assert any(e["url"].endswith("index.html") for e in entries)


def test_network_log_drains_on_read(open_page) -> None:
    spell = open_page()
    spell.get_network_log()
    assert spell.get_network_log() == []
