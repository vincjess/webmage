# Contributing

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
```

## Checks

```sh
pytest                  # unit tests plus integration against every installed engine
ruff check .            # lint
ruff format .           # format
mypy webmage            # types
```

The suite serves `tests/fixtures` over a local HTTP server on an ephemeral port,
so it runs offline and touches no real site.

Browser tests are parameterised over the engines that are importable, so
installing only one of Playwright or Selenium runs that half. Install both
before opening a pull request — the point of the suite is proving the two
engines behave identically, and half of it cannot show that.

## Adding an engine

Implement `Backend` and `ElementAdapter` from `webmage/backends/base.py`, then
register the engine in `webmage/backends/__init__.py`. Nothing else needs to
change: `Spell` and `Rune` only ever talk to those two interfaces, and the whole
integration suite will run against your engine automatically.

Two contracts are easy to miss:

- `find`/`find_all` return `None`/`[]` and never raise.
- `get_attribute` returns the literal HTML attribute, `get_property` the live
  JavaScript property. Selenium conflates the two; do not copy that.
