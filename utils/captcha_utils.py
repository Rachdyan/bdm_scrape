import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from selenium.common.exceptions import TimeoutException, JavascriptException


class PageActions:
    """
    The PageActions class provides methods for interacting with page elements via Selenium WebDriver.  # NOQA
    Used to perform actions such as switching to an iframe, clicking on elements and checking their state.
    """

    def __init__(self, browser):
        """
        Initializing PageActions.

        :param browser: Selenium WebDriver object for interacting with the browser. # NOQA
        """
        self.browser = browser

    def get_clickable_element(self, locator, timeout=30):
        """
        Waits until the element is clickable and returns it.

        :param locator: XPath element locator.
        :param timeout: Timeout in seconds (default 30).
        :return: Clickable element.
        """
        return WebDriverWait(
            self.browser, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, locator)))

    def get_presence_element(self, locator, timeout=30):
        """
        Waits until the element appears in the DOM and returns it.

        :param locator: XPath element locator.
        :param timeout: Timeout in seconds (default 30).
        :return: Found element.
        """
        return WebDriverWait(
            self.browser, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, locator)))

    def switch_to_iframe(self, iframe_locator):
        """
        Switches focus to the iframe of the captcha.

        :param iframe_locator: XPath locator of the iframe.
        """
        iframe = self.get_presence_element(iframe_locator)
        self.browser.switch_to.frame(iframe)
        print("Switched to captcha widget")

    def click_checkbox(self, checkbox_locator):
        """
        Clicks on the checkbox element of the captcha.

        :param checkbox_locator: XPath locator of the captcha checkbox
        """
        checkbox = self.get_clickable_element(checkbox_locator)
        checkbox.click()
        print("Checked the checkbox")

    def switch_to_default_content(self):
        """Returns focus to the main page content from the iframe."""
        self.browser.switch_to.default_content()
        print("Returned focus to the main page content")

    def clicks(self, answer_list):
        """
        Clicks on the image cells in the captcha in accordance with the transmitted list of cell numbers. # NOQA

        :param answer_list: List of cell numbers to click.
        """
        for i in answer_list:
            self.get_presence_element(f"//table//td[@tabindex='{i}']").click()
        print("Cells are marked")

    def click_check_button(self, locator):
        """
        Clicks on the "Check" button on the captcha after selecting images.

        :param locator: XPath locator for the "Check" button.
        """
        time.sleep(1)
        self.get_clickable_element(locator).click()
        print("Pressed the Check button")

    def check_for_image_updates(self):
        """
        Checks if captcha images have been updated using JavaScript.

        :return: Returns True if the images have been updated, False otherwise. # NOQA
        """
        print("Checking for Images updated")
        return self.browser.execute_script("return monitorRequests();")

    # def check_for_image_updates(self):
    #     """
    #     Checks if captcha images have been updated using JavaScript.

    #     :return: True if images were updated within 10 seconds, False
    #     """
    #     print("Checking for Images updated")

    #     try:
    #         # Use execute_async_script to handle the Promise
    #         return self.browser.execute_async_script(
    #             """
    #             const callback = arguments[arguments.length - 1];
    #             monitorRequests()
    #                 .then(result => callback(result))
    #                 .catch(error => {
    #                     console.error('monitorRequests error:', error);
    #                     callback(false);
    #                 });
    #             """
    #         )
    #     except JavascriptException as e:
    #         if "monitorRequests is not defined" in str(e):
    #             try:
    #                 # Wait for function to be defined
    #                 WebDriverWait(self.browser, 10).until(
    #                     lambda d: d.execute_script(
    #                         "return typeof monitorRequests === 'function';"
    #                     )
    #                 )
    #                 # Retry after successful wait
    #                 return self.check_for_image_updates()
    #             except TimeoutException:
    #                 print("JavaScript function 'monitorRequests'"
    #                       "not available after waiting")
    #                 return False
    #         print(f"JavaScript error: {str(e)}")
    #         return False
    #     except Exception as e:
    #         print(f"Unexpected error: {str(e)}")
    #         return False


class CaptchaHelper:
    """
    The CaptchaHelper class provides methods for interacting with captchas
    and executing JavaScript code through Selenium WebDriver. Interaction
    with captchas is carried out using the 2Captcha service.
    """

    def __init__(self, browser, solver):
        """
        Initializing CaptchaHelper.

        :param browser: Selenium WebDriver object for interacting with the browser. # NOQA
        :param solver: 2Captcha object for solving captchas.
        """
        self.browser = browser
        self.solver = solver
        self.page_actions = PageActions(browser)

    def execute_js(self, script):
        """Executes JavaScript code in the browser.

        :param script: A string of JavaScript code to be executed in the context of the current page. # NOQA
        :return: The result of JavaScript execution.
        """
        print("Executing JS")
        return self.browser.execute_script(script)

    def solver_captcha(self, **kwargs):
        """Sends the captcha image to be solved via the 2Captcha service

        :param kwargs: Additional parameters for 2Captcha (for example, base64 image). # NOQA
        :return: The result of solving the captcha or None in case of an error.
        """
        try:
            result = self.solver.grid(**kwargs)
            print("Captcha solved")
            return result
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def pars_answer(self, answer):
        """Parses the response from 2Captcha and returns a list of numbers for clicks. 

        :param answer: Response from 2Captcha in string format (e.g. "OK: 1/2/3"). # NOQA
        :return: List of cell numbers to click.
        """
        numbers_str = answer.split(":")[1]
        number_list = list(map(int, numbers_str.split("/")))
        # Add 3 to go to the correct index.
        new_number_list = [i + 3 for i in number_list]
        print("Parsed the response to a list of cell numbers")
        return new_number_list

    # def is_message_visible(self, locator):
    #     """Checks the visibility of an element with a captcha error message

    #     :param locator: XPath locator of the element to check.
    #     :return: True if the element is visible, otherwise False.
    #     """
    #     try:
    #         element = self.page_actions.get_presence_element(locator)
    #         is_visible = self.browser.execute_script("""
    #             var elem = arguments[0];
    #             var style = window.getComputedStyle(elem);
    #             return !(style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0'); # NOQA
    #         """, element)
    #         return is_visible
    #     except Exception as e:
    #         print(f"Error in is message visible: {e}")
    #         return False

    # def handle_error_messages(
    #         self,
    #         l_try_again,
    #         l_select_more,
    #         l_dynamic_more,
    #         l_select_something):
    #     """
    #     Checks for error messages on the captcha and returns True if they are visible. # NOQA

    #     :param l_try_again: Locator for the "Try again" message.
    #     :param l_select_more: Locator for the "Select more" message.
    #     :param l_dynamic_more: Locator for dynamic error.
    #     :param l_select_something: Locator for the "Select something".
    #     :return: True if any of the error messages are visible, other False.
    #     """
    #     time.sleep(1)
    #     if self.is_message_visible(l_try_again):
    #         return True
    #     elif self.is_message_visible(l_select_more):
    #         return True
    #     elif self.is_message_visible(l_dynamic_more):
    #         return True
    #     elif self.is_message_visible(l_select_something):
    #         return True
    #     print("No error messages")
    #     return False

    def handle_error_messages(
            self,
            l_try_again,
            l_select_more,
            l_dynamic_more,
            l_select_something):
        """
        Checks for error messages using SeleniumBase's visibility checks
        """
        # Optional: Add brief wait for UI updates (adjust as needed)
        time.sleep(0.5)

        # Check all error conditions with proper element existence verification
        errors_detected = (
            self._is_visible_sb(l_try_again) or
            self._is_visible_sb(l_select_more) or
            self._is_visible_sb(l_dynamic_more) or
            self._is_visible_sb(l_select_something)
        )

        if errors_detected:
            print("Captcha error message detected")
        return errors_detected

    def _is_visible_sb(self, selector):
        """Safe visibility check with SeleniumBase"""
        try:
            # Uses SeleniumBase's is_element_visible which handles:
            # - Element presence
            # - Visibility
            # - Stale element retries
            print(f"Checking {selector} visibility..")
            return self.browser.is_element_visible(selector)
        except Exception as e:
            print(f"Visibility check error for {selector}: {str(e)}")
            return False

    def load_js_script(self, file_path):
        """
        Loads JavaScript code from a file.

        :param file_path: Path to the file with JavaScript code.
        :return: A string containing the contents of the file.
        """
        with open(file_path, 'r') as file:
            return file.read()
