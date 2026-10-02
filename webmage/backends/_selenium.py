"""Selenium backend.

Driver binaries are resolved by Selenium Manager, built into Selenium since
4.6, which is why ``webdriver_manager`` is no longer a dependency. Passing an
explicit ``driver_path`` is still supported and now actually works: in 1.0.x the
whole driver-construction block sat inside ``if driver_path is None``, so
supplying one left ``self.driver`` unset and the next line raised
``AttributeError``.
"""

from __future__ import annotations

import json
from typing import Any

from ..exceptions import (
    EngineNotAvailableError,
    JavaScriptError,
    WaitTimeoutError,
)
from .base import Backend, ElementAdapter

__all__ = ["SeleniumBackend"]

_ALIASES = {"chromium": "chrome", "google-chrome": "chrome", "ff": "firefox"}
_SUPPORTED = ("chrome", "firefox", "edge", "safari")

# Chrome and Edge took the new headless mode in 109; the bare --headless flag
# that 1.0.x used now selects the old one, which several sites detect.
_CHROMIUM_HEADLESS = "--headless=new"


class SeleniumElement(ElementAdapter):
    """Wraps a ``selenium.webdriver.remote.webelement.WebElement``."""

    __slots__ = ("_el", "_driver")

    def __init__(self, element: Any, driver: Any) -> None:
        self._el = element
        self._driver = driver

    @property
    def text(self) -> str:
        return self._el.text

    @property
    def tag_name(self) -> str:
        return self._el.tag_name.lower()

    @property
    def inner_html(self) -> str:
        return self._el.get_attribute("innerHTML") or ""

    @property
    def outer_html(self) -> str:
        return self._el.get_attribute("outerHTML") or ""

    def get_attribute(self, name: str) -> str | None:
        # get_dom_attribute, not get_attribute: Selenium's get_attribute falls
        # back to the JS property, which makes href absolute and value reflect
        # typing. Playwright has no such fallback, so using it here would make
        # the two engines disagree.
        return self._el.get_dom_attribute(name)

    def get_property(self, name: str) -> Any:
        return self._el.get_property(name)

    def attributes(self) -> dict[str, str]:
        props = self._el.get_property("attributes") or []
        out: dict[str, str] = {}
        for attr in props:
            name = attr["nodeName"]
            value = self._el.get_dom_attribute(name)
            if value is not None:
                out[name] = value
        return out

    def find(self, css_selector: str) -> ElementAdapter | None:
        from selenium.webdriver.common.by import By

        found = self._el.find_elements(By.CSS_SELECTOR, css_selector)
        return SeleniumElement(found[0], self._driver) if found else None

    def find_all(self, css_selector: str) -> list[ElementAdapter]:
        from selenium.webdriver.common.by import By

        return [
            SeleniumElement(el, self._driver)
            for el in self._el.find_elements(By.CSS_SELECTOR, css_selector)
        ]

    def click(self) -> None:
        self._el.click()

    def clear(self) -> None:
        self._el.clear()

    def type(self, text: str) -> None:
        self._el.send_keys(text)

    def screenshot(self) -> bytes:
        return self._el.screenshot_as_png

    def execute_js(self, script: str, *args: Any) -> Any:
        raw = [a.unwrap() if isinstance(a, SeleniumElement) else a for a in args]
        return self._driver.execute_script(script, self._el, *raw)

    def unwrap(self) -> Any:
        """The underlying Selenium element, for callers who need to drop down."""
        return self._el


class SeleniumBackend(Backend):
    name = "selenium"

    def __init__(
        self,
        browser: str = "chrome",
        headless: bool = False,
        driver_path: str | None = None,
        capture_network: bool = False,
    ) -> None:
        try:
            from selenium import webdriver
        except ImportError as exc:  # pragma: no cover - depends on install extras
            raise EngineNotAvailableError(
                "The selenium engine needs Selenium. Install it with "
                "`pip install webmage[selenium]`."
            ) from exc

        self.browser = self._normalise_browser(browser, _ALIASES, _SUPPORTED, "selenium")
        self.headless = headless
        self._capture_network = capture_network and self.browser in ("chrome", "edge")
        self.driver = self._build_driver(webdriver, driver_path)

    # -- construction -----------------------------------------------------

    def _build_driver(self, webdriver: Any, driver_path: str | None) -> Any:
        builders = {
            "chrome": (webdriver.ChromeOptions, webdriver.Chrome, "chrome"),
            "edge": (webdriver.EdgeOptions, webdriver.Edge, "edge"),
            "firefox": (webdriver.FirefoxOptions, webdriver.Firefox, "firefox"),
            "safari": (webdriver.SafariOptions, webdriver.Safari, "safari"),
        }
        options_cls, driver_cls, kind = builders[self.browser]
        options = options_cls()

        if self.headless:
            if kind in ("chrome", "edge"):
                options.add_argument(_CHROMIUM_HEADLESS)
            elif kind == "firefox":
                options.add_argument("-headless")
            # Safari has no headless mode; honouring the flag is impossible.

        if kind in ("chrome", "edge"):
            options.add_argument("--ignore-certificate-errors")
            if self._capture_network:
                options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        if driver_path:
            service = self._service_for(kind, driver_path)
            return driver_cls(service=service, options=options)
        # No path: Selenium Manager locates or downloads the driver itself.
        return driver_cls(options=options)

    @staticmethod
    def _service_for(kind: str, driver_path: str) -> Any:
        if kind == "chrome":
            from selenium.webdriver.chrome.service import Service as ChromeService

            return ChromeService(executable_path=driver_path)
        if kind == "edge":
            from selenium.webdriver.edge.service import Service as EdgeService

            return EdgeService(executable_path=driver_path)
        if kind == "firefox":
            from selenium.webdriver.firefox.service import Service as FirefoxService

            return FirefoxService(executable_path=driver_path)
        from selenium.webdriver.safari.service import Service as SafariService

        return SafariService(executable_path=driver_path)

    # -- page state -------------------------------------------------------

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    @property
    def title(self) -> str:
        return self.driver.title

    @property
    def page_source(self) -> str:
        return self.driver.page_source

    def goto(self, url: str) -> None:
        self.driver.get(url)

    # -- querying ---------------------------------------------------------

    def _root(self) -> Any:
        return self.driver

    def find(self, css_selector: str) -> ElementAdapter | None:
        from selenium.webdriver.common.by import By

        found = self._root().find_elements(By.CSS_SELECTOR, css_selector)
        return SeleniumElement(found[0], self.driver) if found else None

    def find_all(self, css_selector: str) -> list[ElementAdapter]:
        from selenium.webdriver.common.by import By

        return [
            SeleniumElement(el, self.driver)
            for el in self._root().find_elements(By.CSS_SELECTOR, css_selector)
        ]

    def wait_for(self, css_selector: str, timeout: float, state: str) -> ElementAdapter:
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        from selenium.webdriver.support.ui import WebDriverWait

        conditions = {
            "attached": ec.presence_of_element_located,
            "visible": ec.visibility_of_element_located,
            "hidden": ec.invisibility_of_element_located,
        }
        try:
            WebDriverWait(self.driver, timeout).until(
                conditions[state]((By.CSS_SELECTOR, css_selector))
            )
        except TimeoutException as exc:
            raise WaitTimeoutError(
                f"{css_selector!r} was not {state} after {timeout}s."
            ) from exc

        if state == "hidden":
            # Nothing meaningful to hand back; keep the return type honest.
            found = self.find(css_selector)
            if found is not None:
                return found
            raise WaitTimeoutError(f"{css_selector!r} is gone from the DOM.")

        found = self.find(css_selector)
        if found is None:  # pragma: no cover - the wait above guarantees it
            raise WaitTimeoutError(f"{css_selector!r} vanished after the wait.")
        return found

    # -- scripting --------------------------------------------------------

    def execute_js(self, script: str, *args: Any) -> Any:
        from selenium.common.exceptions import JavascriptException

        raw = [a.unwrap() if isinstance(a, SeleniumElement) else a for a in args]
        try:
            return self.driver.execute_script(script, *raw)
        except JavascriptException as exc:
            raise JavaScriptError(str(exc)) from exc

    # -- network ----------------------------------------------------------

    def network_log(self) -> list[dict[str, Any]]:
        if not self._capture_network:
            return []
        entries: list[dict[str, Any]] = []
        for raw in self.driver.get_log("performance"):
            message = json.loads(raw["message"])["message"]
            method = message.get("method", "")
            params = message.get("params", {})
            if method == "Network.requestWillBeSent":
                request = params.get("request", {})
                entries.append(
                    {
                        "type": "request",
                        "url": request.get("url"),
                        "method": request.get("method"),
                        "status": None,
                        "resource_type": params.get("type"),
                        "headers": request.get("headers", {}),
                    }
                )
            elif method == "Network.responseReceived":
                response = params.get("response", {})
                entries.append(
                    {
                        "type": "response",
                        "url": response.get("url"),
                        "method": None,
                        "status": response.get("status"),
                        "resource_type": params.get("type"),
                        "headers": response.get("headers", {}),
                    }
                )
        return entries

    # -- tabs and frames --------------------------------------------------

    def open_tab(self, url: str) -> None:
        self.driver.switch_to.new_window("tab")
        self.driver.get(url)

    def close_tab(self) -> None:
        self.driver.close()
        handles = self.driver.window_handles
        if handles:
            self.driver.switch_to.window(handles[0])

    def switch_to_frame(self, css_selector: str) -> None:
        from selenium.webdriver.common.by import By

        self.driver.switch_to.frame(
            self.driver.find_element(By.CSS_SELECTOR, css_selector)
        )

    def switch_to_default_content(self) -> None:
        self.driver.switch_to.default_content()

    # -- teardown ---------------------------------------------------------

    def close(self) -> None:
        # quit(), not close(): close() drops one tab and leaves the driver
        # process alive, which is how 1.0.x leaked chromedriver instances.
        self.driver.quit()
