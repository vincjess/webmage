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

## Releasing

The version in `pyproject.toml` is the release trigger. To ship:

1. Bump `version` in `pyproject.toml`.
2. Move the `CHANGELOG.md` entry from unreleased to the new version and date.
3. Merge to `main`.

`.github/workflows/release.yml` compares that version against PyPI. If it is
already published it does nothing; if it is new it runs the full suite and, only
on green, publishes.

Uploads use PyPI Trusted Publishing over OIDC, so there is no API token stored
in the repository. PyPI checks that the request comes from this repository's
`release.yml` running in the `pypi` environment, and issues a short-lived token.
Changing the workflow filename or the environment name means updating the
publisher entry on PyPI to match, or uploads will be rejected.

PyPI uploads are immutable: a version number cannot be reused, even after a
delete. A botched release is fixed by bumping to the next patch version, never
by re-publishing.

## Adding an engine

Implement `Backend` and `ElementAdapter` from `webmage/backends/base.py`, then
register the engine in `webmage/backends/__init__.py`. Nothing else needs to
change: `Spell` and `Rune` only ever talk to those two interfaces, and the whole
integration suite will run against your engine automatically.

Two contracts are easy to miss:

- `find`/`find_all` return `None`/`[]` and never raise.
- `get_attribute` returns the literal HTML attribute, `get_property` the live
  JavaScript property. Selenium conflates the two; do not copy that.
