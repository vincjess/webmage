# WebMage

[![PyPI](https://img.shields.io/pypi/v/webmage.svg)](https://pypi.org/project/webmage/)
[![Python](https://img.shields.io/pypi/pyversions/webmage.svg)](https://pypi.org/project/webmage/)
[![License](https://img.shields.io/pypi/l/webmage.svg)](LICENSE)

One small, readable API over **Playwright** and **Selenium**, for scraping pages
that only exist after JavaScript has run.

Browser automation libraries are powerful and verbose. WebMage keeps the parts a
scraper actually reaches for — select, click, scroll, read, run some JS — and
puts the same names on top of either engine, so switching engines is one keyword
argument rather than a rewrite.

```python
from webmage import WebMage

with WebMage("https://example.com", headless=True) as spell:
    print(spell.wait_for("h1").text)
    print(spell.select_all("a")["href"])
```

## Install

The engines are optional extras, so you only install the one you want:

```sh
pip install "webmage[playwright]"   # recommended; brings its own browsers
python -m playwright install        # one-time browser download

pip install "webmage[selenium]"     # uses browsers already on the machine
pip install "webmage[all]"          # both
```

Playwright is worth preferring. It pins and downloads its own browser builds, so
there is no driver to install and no browser/driver version skew — far and away
the most common reason a scraper that worked last year does not today.

## Engines and browsers

| Engine | Browsers | Browser install | Notes |
| --- | --- | --- | --- |
| `playwright` | `chromium`, `firefox`, `webkit` | `playwright install` | Self-contained; reaches WebKit on any OS |
| `selenium` | `chrome`, `firefox`, `edge`, `safari` | uses what you have | Drivers resolved by Selenium Manager |

Browser names are normalised per engine, so `browser="chrome"` works on both —
Playwright maps it to Chromium, Selenium to Chrome. The default `engine="auto"`
picks whichever is installed, preferring Playwright.

```python
WebMage(url, engine="playwright", browser="webkit")
WebMage(url, engine="selenium", browser="firefox", headless=True)
```

## The three objects

**`Spell`** is the browser session, returned by `WebMage(...)`. Use it as a
context manager and the browser always closes, including when something raises.

**`Rune`** is one element. `spell.select(css)` returns one or `None`.

**`RuneList`** is what `select_all` returns: a real `list` that can also be
indexed by attribute name, which is usually what you want when scraping.

```python
links = spell.select_all("nav a")

links[0].text          # 'Home'          — one element
links["href"]          # ['/a', '/b']    — one attribute from all of them
links.text             # ['Home', 'About']
links[:2]              # a RuneList
```

## Finding things

```python
spell.select("h1")                     # first match, or None
spell.select_all(".item")              # RuneList, possibly empty
spell.require("#must-exist")           # raises ElementNotFoundError if missing
spell.wait_for("#loaded", timeout=10)  # waits, then returns it
```

`wait_for` is the one to reach for on a slow page. It returns the moment the
element is ready instead of sleeping a fixed interval, and raises
`WaitTimeoutError` if it never arrives. `state` may be `"visible"` (default),
`"attached"` or `"hidden"`.

Runes nest, so you can scope a query to a subtree:

```python
row = spell.select("#results")
for item in row.select_all(".item"):
    print(item.text, item["data-id"])
```

### Attributes vs properties

`rune[name]` is the **literal HTML attribute**. `rune.get_property(name)` is the
**live JavaScript property**.

```python
link["href"]                  # '/one'                    — as written in the markup
link.get_property("href")     # 'https://site.com/one'    — as the browser resolved it

field["value"]                # 'preset'   — the original attribute
field.get_property("value")   # 'typed'    — what the field holds right now
```

Worth knowing because Selenium's own `get_attribute` quietly returns the property
when one exists, so the same call used to give different answers on different
engines. WebMage keeps them distinct and identical across both. Missing
attributes return `None` rather than raising.

## Interacting

```python
spell.click("button.submit")
spell.click_all(".expand", wait_interval=0.5)
spell.type("#search", "query")
spell.clear("#search")

png = spell.get_screenshot("#chart")     # bytes
rune.click(); rune.type("x"); rune.clear(); rune.screenshot()
```

## Scrolling

Four methods, for the two axes that matter: how far each step goes, and whether
there is a fixed number of steps.

```python
spell.scroll(1.0, 5)                       # jump to the bottom, up to 5 times
spell.scroll_by_pixels(0.5, 10, pixels=400)  # 400px at a time, 10 times
spell.infinite_scroll(1.0)                 # until the page stops growing
spell.infinite_scroll_by_pixels(0.5, pixels=400)
```

Each returns the number of scrolls performed and stops early once the page stops
growing. The pixel variants are gentler, for pages that only load content for
viewports they believe a human has passed through.

Pass `selector=` for a custom scrolling container, `callback=` to run after every
step, and `max_scrolls=` to cap the infinite variants:

```python
rows = []
spell.infinite_scroll(
    1.0,
    selector="#feed",
    callback=lambda s: rows.extend(s.select_all(".row").text),
    max_scrolls=50,
)
```

## Running JavaScript

`cast_js` takes a function body. Extra arguments arrive as `arguments[0]`,
`arguments[1]` and so on, and `return` hands a value back — the same script text
on either engine.

```python
spell.cast_js("return document.title;")
spell.cast_js("return document.querySelectorAll(arguments[0]).length;", ".item")
rune.cast_js("return arguments[0].getBoundingClientRect().top;")
```

Removing things — cookie banners, overlays, anything in the way:

```python
spell.destroy("#cookie-banner")
spell.destroy_all(".ad")
rune.destroy()
```

## Frames and tabs

```python
spell.switch_frames("#checkout-iframe")
spell.select("#card-number").type("4242...")
spell.switch_to_default_content()

def read_detail(s, payload):
    return s.select("h1").text

title = spell.open_tab("https://example.com/item/1", callback=read_detail)
```

`open_tab` opens a second tab, runs the callback there, then closes it and
returns whatever the callback returned — even if the callback raises.

## Network log

Useful for data that only exists in a response: image and video URLs, or a JSON
endpoint the page calls.

```python
with WebMage(url, capture_network=True) as spell:
    for entry in spell.get_network_log():
        if entry["type"] == "response" and entry["status"] == 200:
            print(entry["url"])
```

Entries are normalised to the same shape on both engines — `type`, `url`,
`method`, `status`, `resource_type`, `headers`. The log drains on read, so hold
on to what you need. It is off by default because capturing costs throughput.

## Errors

Everything inherits from `WebMageError`:

| Exception | Raised when |
| --- | --- |
| `ElementNotFoundError` | `require` or an interaction found no match |
| `WaitTimeoutError` | `wait_for` expired |
| `EngineNotAvailableError` | the requested engine is not installed |
| `BrowserNotSupportedError` | the engine cannot drive that browser |
| `JavaScriptError` | a script failed in the page |

## Dropping down

WebMage covers the common cases, not every case. When you need the real driver:

```python
spell._backend.driver        # the Selenium WebDriver
rune.unwrap()                # the underlying Selenium or Playwright element
```

## Upgrading from 1.x

2.0 renames every method from camelCase to snake_case and is not drop-in
compatible. [CHANGELOG.md](CHANGELOG.md) has the full mapping and the two
behaviour changes worth checking.

## License

MIT — see [LICENSE](LICENSE).
