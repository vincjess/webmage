"""Shared fixtures.

Pages are served over real HTTP from ``tests/fixtures`` rather than ``file://``
so that navigation, iframes and network capture behave as they do in the wild.
Nothing here touches the public internet, so the suite runs offline.
"""

from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # noqa: D102 - silence the server
        pass


@pytest.fixture(scope="session")
def server() -> object:
    """A local static file server; yields its base URL."""
    handler = functools.partial(_QuietHandler, directory=str(FIXTURES))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def _installed_engines() -> list[str]:
    from webmage.backends import available_engines

    return available_engines()


@pytest.fixture(scope="module", params=_installed_engines())
def spell(request: pytest.FixtureRequest, server: str):
    """One headless browser per engine, reused across a module."""
    from webmage import WebMage

    session = WebMage(
        f"{server}/index.html",
        engine=request.param,
        headless=True,
        capture_network=True,
    )
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def open_page(spell, server: str):
    """Reload a fixture page, so each test starts from a clean DOM."""

    def _open(name: str = "index.html"):
        spell.change_url(f"{server}/{name}")
        return spell

    return _open
