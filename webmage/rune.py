from .rune_list import RuneList
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By

class Rune:
    def __init__(self, selenium_rune, driver):
        self.selenium_rune = selenium_rune
        self.driver = driver
        self.text = selenium_rune.text
        self.outerHTML = selenium_rune.get_attribute('outerHTML')
        self.tagName = selenium_rune.get_attribute('tagName').lower()

    def __repr__(self):
        return f'{self.outerHTML}'

    def __str__(self):
        return f'{self.outerHTML}'

    def __getitem__(self, item_request):
        value = self.selenium_rune.get_attribute(item_request)
        return value

    def __contains__(self, item_request):
        value = self.selenium_rune.get_attribute(item_request)
        return value

    def castJS(self, javaScript, arguments=None):
        return self.driver.execute_script(javaScript, arguments)

    def select(self, css_selector):
        return Rune(self.selenium_rune.find_element(By.CSS_SELECTOR ,css_selector), self.driver)

    def selectAll(self, css_selector):
        return RuneList([Rune(i, self.driver) for i in self.selenium_rune.find_elements(By.CSS_SELECTOR, css_selector)])

    def getAttributes(self):
        self.attributes = {}
        for attribute in self.selenium_rune.get_property('attributes'):
            self.attributes[attribute['nodeName']] = self.selenium_rune.get_attribute(attribute['nodeName'])

    def click(self):
        self.selenium_rune.click()


    def destroy(self, css_selector=None):
        # If no css_selector is provided, then delete the element itself.
        if css_selector == None:
            self.castJS("""
            arguments[0].remove();
            """, self.selenium_rune)        
        # If a css_selector is provided, then search for an element within the element to delete.
        else:
            self.castJS(f"""
            let els = arguments[0].querySelectorAll('{css_selector}');
            els.length > 0 ? els[0].remove() : null;
            """, self.selenium_rune)

    def destroyAll(self, css_selector):
        self.castJS(f"""
        arguments[0].querySelectorAll('{css_selector}')
            .forEach(el => el.remove());
        """, self.selenium_rune)
