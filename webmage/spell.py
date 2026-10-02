import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from time import sleep
from selenium.common.exceptions import JavascriptException
import json
# Runes
from .rune_list import RuneList
from .rune import Rune

class Spell:
    def __init__(self, url, driver_path=None, ghost=False, browser='chrome'):
        self.url = url
        self.driver_path = driver_path
        self.ghost = ghost
        self.browser = browser

        self.initialize_driver()


    def initialize_driver(self):
        # Get chrome driver if no path is given.
        if self.driver_path == None:
            if 'chrome' in self.browser:
                options = webdriver.ChromeOptions()
                if self.ghost:
                    options.add_argument('--headless')
                # Remove all of the nonsense errors that are printed out.
                options.add_argument('--ignore-certificate-errors')
                options.add_argument('--ignore-ssl-errors')
                service = ChromeService()
                self.driver = webdriver.Chrome(service=service, options=options)
            elif self.browser == 'firefox':
                options = webdriver.FirefoxOptions()
                if self.ghost:
                    options.add_argument('--headless')
                # Remove all of the nonsense errors that are printed out.
                options.add_argument('--ignore-certificate-errors')
                options.add_argument('--ignore-ssl-errors')
                service = FirefoxService()
                self.driver = webdriver.Firefox(service=service, options=options)
            else:
                raise Exception(f'{self.browser} is not a valid browser.')
        self.driver.get(self.url)


    def close(self):
        self.driver.close()


    # For selecting first item based on CSS selector.
    def select(self, css_selector):
        elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
        if len(elements) > 0:
            return Rune(elements[0], self.driver)
        else:
            return None


    # For selecting first item based on CSS selector.
    def selectAll(self, css_selector):
        return RuneList([Rune(i, self.driver)for i in self.driver.find_elements(By.CSS_SELECTOR, css_selector)])

    # Changes the URL of the original soup.
    def changeUrl(self, url, retry=True):
        if retry == False:
            self.driver.get(url)
            self.url = self.driver.current_url
        else:
            success = False
            while success == False:
                try:
                    self.driver.get(url)
                    self.url = self.driver.current_url
                    success = True
                except:
                    print('Error! Trying in 3 few seconds...')
                    self.wait(3)

    # Click on a element by its css selector
    def click(self, css_selector):
        self.driver.find_element(By.CSS_SELECTOR, css_selector).click()

    # Click on all elements by its css selector. Waits 0.25 between each click by default
    def clickAll(self, css_selector, wait_interval=0.25):
        clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector).click()
        for el in clickable_elements:
            el.click()
            self.wait(wait_interval)

    def scroll(self, wait_interval, scroll_count, scroll_css_selector="document.scrollingElement", callback=None, verbose=True):
        counter = 1

        # Make the CSS Selector into a querySelector
        if scroll_css_selector != 'document.scrollingElement':
            scroll_css_selector = f'document.querySelector("{scroll_css_selector}")'

        last_height = self.driver.execute_script(f"return {scroll_css_selector}.scrollHeight")

        while counter <= scroll_count:
            self.driver.execute_script(f"{scroll_css_selector}.scrollTop = {scroll_css_selector}.scrollHeight;")
            # Wait to load page
            self.wait(wait_interval)
            if verbose:
                print(f'\rScroll #{counter} completed!', end='')
            counter += 1
            
            # Execute callback function
            if callback:
                callback(self)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script(f"return {scroll_css_selector}.scrollHeight")

            if new_height == last_height:
                break
            last_height = new_height
        # Go to next line after scroll completion.
        print('')


    def scrollByPixels(self, wait_interval, scroll_count, scroll_pixel_length=500, scroll_css_selector="document.scrollingElement", callback=None, verbose=True):
        counter = 1

        # Make the CSS Selector into a querySelector
        if scroll_css_selector != 'document.scrollingElement':
            scroll_css_selector = f'document.querySelector("{scroll_css_selector}")'

        # last_height = self.driver.execute_script(f"return {scroll_css_selector}.scrollHeight")
        max_height = int(self.castJS(f'return {scroll_css_selector}.scrollHeight'))
        i = 0

        while counter <= scroll_count:
            self.castJS(f'{scroll_css_selector}.scrollTop = {i}')
            i += scroll_pixel_length
            # Wait to load page
            self.wait(wait_interval)
            if verbose:
                print(f'\rScroll #{counter} completed!', end='')
            counter += 1
            # Execute callback function
            if callback:
                callback(self)

            # If page is dynamically adding content to page, max_height will increment.
            max_height = int(self.castJS(f'return {scroll_css_selector}.scrollHeight'))

        # Go to next line after scroll completion.
        print('')


    def infiniteScroll(self, wait_interval, scroll_css_selector="document.scrollingElement", callback=None, verbose=True):
        counter = 1

        # Make the CSS Selector into a querySelector
        if scroll_css_selector != 'document.scrollingElement':
            scroll_css_selector = f'document.querySelector("{scroll_css_selector}")'

        last_height = self.driver.execute_script(f"return {scroll_css_selector}.scrollHeight")

        while True:
            self.driver.execute_script(f"{scroll_css_selector}.scrollTop = {scroll_css_selector}.scrollHeight;")
            # Wait to load page
            self.wait(wait_interval)
            if verbose:
                print(f'\rScroll #{counter} completed!', end='')
            counter += 1
            # Execute callback function
            if callback:
                callback(self)
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script(f"return {scroll_css_selector}.scrollHeight")
            # Break if at the bottom of the page.
            if new_height == last_height:
                break
            last_height = new_height
        # Go to next line after scroll completion.
        print('')


    def infiniteScrollByPixels(self, wait_interval, scroll_pixel_length=500, scroll_css_selector="document.scrollingElement", callback=None, verbose=True):
        counter = 1

        # Make the CSS Selector into a querySelector
        if scroll_css_selector != 'document.scrollingElement':
            scroll_css_selector = f'document.querySelector("{scroll_css_selector}")'

        # last_height = self.driver.execute_script(f"return {scroll_css_selector}.scrollHeight")
        max_height = int(self.castJS(f'return {scroll_css_selector}.scrollHeight'))
        i = 0

        while max_height > i:
            self.castJS(f'{scroll_css_selector}.scrollTop = {i}')
            i += scroll_pixel_length
            # Wait to load page
            self.wait(wait_interval)
            if verbose:
                print(f'\rScroll #{counter} completed!', end='')
            counter += 1
            # Execute callback function
            if callback:
                callback(self)

            # If page is dynamically adding content to page, max_height will increment.
            max_height = int(self.castJS(f'return {scroll_css_selector}.scrollHeight'))

        # Go to next line after scroll completion.
        print('')

    # Wait a certain amount of seconds to continue code.
    def wait(self, time_interval):
        sleep(time_interval)

    # Gets the end name of the URL
    def getSlug(self):
        # Get portion of URL after last forward slash.
        slug =  re.sub(r'^.+?/([^/]+?)$', r'\1', self.url)
        # Remove any hashes
        slug = re.sub(r'#[^#]+?$', r'', slug)
        # Remove any queries
        slug = re.sub(r'\?.+?$', r'', slug)
        return slug



    def getNetworkLog(self):
        filtered_entries = []
        # Get the full performance log
        logs = self.driver.get_log('performance')

        for entry in logs:
            # Parse the entry.
            log = json.loads(entry["message"])["message"]
            # Filter for only these 3 logs.
            if (
                "Network.response" in log["method"]
                or "Network.request" in log["method"]
                or "Network.webSocket" in log["method"]
            ):
                filtered_entries.append(log)
        return filtered_entries


    def castJS(self, javaScript, arguments=None):
        return self.driver.execute_script(javaScript, arguments)


    def openTab(self, url, callback=False, payload=None):
        # Open a new tab to the url
        self.castJS(f"window.open('{url}', '_blank');")
        # Get list of all tabs (handles)
        handles = self.driver.window_handles
        # Make focus on second handle
        self.driver.switch_to.window(handles[1])
        # Pause to allow tab to load
        self.wait(3)
        # Call the callback with the payload arguments
        if callback:
            payload = callback(self, payload)

        # Close the tab
        self.driver.close()
        # Switch focus back to main handle
        self.driver.switch_to.window(handles[0])

        return payload

    def getScreenshot(self, css_selector):
        return self.driver.find_element(By.CSS_SELECTOR, css_selector).screenshot_as_png

    def clear(self, css_selector):
        self.driver.find_element(By.CSS_SELECTOR, css_selector).clear()

    def type(self, css_selector, string):
        self.driver.find_element(By.CSS_SELECTOR, css_selector).send_keys(string)

    def destroy(self, css_selector):
        try:
            self.castJS(f"""
            let els = document.querySelectorAll('{css_selector}');
            els.length > 0 ? els[0].remove() : null;
            """)
        except JavascriptException as err:
            print('WebMage tried to destroyed an element that does not exist.')

    def destroyAll(self, css_selector):
        try:
            self.castJS(f"""
            document.querySelectorAll('{css_selector}')
                .forEach(el => el.remove());
            """)
        except JavascriptException as err:
            print('WebMage tried to destroyed an element that does not exist.')

    def switchToDefaultContent(self):
        self.driver.switch_to.default_content()

    def switchFrames(self, css_selector):
        self.driver.switch_to.frame(self.driver.find_element(By.CSS_SELECTOR, css_selector))

    def getPageSource(self):
        return self.driver.page_source
