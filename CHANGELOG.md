# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] — unreleased

A rewrite around pluggable engines. Every method name changed from camelCase to
snake_case, so this release is not drop-in compatible with 1.0.x; see
[Upgrading](#upgrading-from-10x) below.

### Added

- **Playwright engine**, alongside Selenium. Playwright ships its own browsers,
  so there is no driver to install and no browser/driver version skew — the
  usual reason a working scraper stops working. It also reaches WebKit.
- `engine="auto"` (the default) picks whichever engine is installed, preferring
  Playwright.
- Browsers: Chromium, Firefox and WebKit via Playwright; Chrome, Firefox, Edge
  and Safari via Selenium. Names are normalised per engine, so `browser="chrome"`
  works on both.
- `Spell.wait_for(selector, timeout, state)` — an explicit wait that returns as
  soon as the element is ready and raises `WaitTimeoutError` if it never is.
  Previously the only option was sleeping a fixed interval.
- `Spell.require(selector)`, which raises `ElementNotFoundError` instead of
  returning `None`.
- Context-manager support, so the browser closes even when the body raises:
  `with WebMage(url) as spell:`.
- `Rune.get_property(name)` for live JavaScript properties, distinct from
  attribute access.
- `RuneList.text` and `RuneList.attributes()`.
- An exception hierarchy rooted at `WebMageError`.
- Type hints throughout, with `py.typed` so downstream type-checkers use them.
- A test suite that runs against every installed engine, and CI across Python
  3.10–3.13.

### Fixed

- `click_all` called `.click()` on the *list* returned by `find_elements`, so it
  raised `AttributeError` on every call. It had never worked.
- Passing `driver_path` left `self.driver` unset, because the entire driver
  construction sat inside `if driver_path is None`. Supplying the documented
  argument raised `AttributeError` immediately.
- `repr()` of a `RuneList` raised `AttributeError`: it read `.name`, which `Rune`
  has never defined.
- Slicing a `RuneList` matched neither branch of `__getitem__` and silently
  returned `None`.
- `rune.attributes` did not exist until `getAttributes()` had been called, though
  the documentation presented it as always available. It is now a property.
- `close()` called `driver.close()`, which drops a single tab and leaves the
  driver process running. It now calls `quit()`.
- `destroy()` and `destroy_all()` interpolated the selector into JavaScript
  source, so any selector containing a quote was a syntax error. Selectors are
  now passed as script arguments.
- The scroll helpers interpolated selectors into source in the same way.
- `changeUrl`'s retry loop was infinite and sat behind a bare `except:`, which
  also swallowed `KeyboardInterrupt`. Retries are now a finite, explicit count.
- `infinite_scroll` had no upper bound; a page that kept appending content looped
  forever. `max_scrolls` is now available.
- `get_slug()` returned the entire URL for URLs with no path. It now parses with
  `urllib.parse`.
- Headless Chrome and Edge used the pre-109 `--headless` flag, which selects the
  old headless mode. Now `--headless=new`.
- `Rune` cached `text`, `outerHTML` and `tagName` at construction, so a rune held
  across a click or scroll reported stale content. All are read live.
- Attribute access returned different things on different engines: Selenium's
  `get_attribute` silently prefers the JavaScript property, so `rune["href"]` was
  absolute under Selenium and relative under Playwright, and `rune["value"]`
  reflected typing on one engine but not the other. `rune[name]` is now the
  literal HTML attribute on both; use `get_property` for the live value.

### Changed

- **All methods are snake_case.** `changeUrl` → `change_url`, `selectAll` →
  `select_all`, `castJS` → `cast_js`, `getSlug` → `get_slug`, `getNetworkLog` →
  `get_network_log`, `getPageSource` → `get_page_source`, `getScreenshot` →
  `get_screenshot`, `openTab` → `open_tab`, `switchFrames` → `switch_frames`,
  `switchToDefaultContent` → `switch_to_default_content`, `scrollByPixels` →
  `scroll_by_pixels`, `infiniteScroll` → `infinite_scroll`,
  `infiniteScrollByPixels` → `infinite_scroll_by_pixels`.
- `ghost=` is now `headless=`.
- The scroll methods take `selector=None` instead of the
  `scroll_css_selector="document.scrollingElement"` sentinel string, and return
  the number of scrolls performed.
- `verbose` defaults to `False` and progress goes to stderr, so it cannot
  contaminate piped output.
- `get_network_log()` returns normalised dicts — `type`, `url`, `method`,
  `status`, `resource_type`, `headers` — identical across engines, rather than
  raw Chrome DevTools messages. It requires `capture_network=True`.
- Driver binaries come from Selenium Manager, built into Selenium since 4.6.
- Python 3.10 or newer is required (3.9 reached end of life in October 2025).

### Removed

- Dependencies on `webdriver_manager`, `undetected_chromedriver` and
  `beautifulsoup4`. All three were declared in 1.0.3 and imported by none of its
  code. The engines are now optional extras, so `pip install webmage` pulls
  nothing it does not need.
- `support.py`, dead since the 1.0.0 rewrite.

### Upgrading from 1.0.x

```python
# 1.0.x
from webmage import WebMage
spell = WebMage('https://example.com', ghost=True, browser='chrome')
links = spell.selectAll('a')
spell.changeUrl('https://example.com/next')
spell.close()

# 2.0
from webmage import WebMage
with WebMage('https://example.com', headless=True, browser='chrome') as spell:
    links = spell.select_all('a')
    spell.change_url('https://example.com/next')
```

Two behaviour changes to check rather than rename: `rune['href']` is now the
literal attribute rather than a resolved absolute URL (use
`rune.get_property('href')` for the old value), and `get_network_log()` needs
`capture_network=True` and returns a normalised shape.

## [1.0.3] — 2024-04-10

Last release of the 1.x line. Its source was never committed to this repository
and was recovered from the published sdist; the history before this point
reflects 0.0.11.
