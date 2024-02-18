import os
import pickle

from selenium.webdriver.remote.webdriver import WebDriver

# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false


class CookieStorage:
    """A helper for saving and loading browser cookies"""

    def __init__(self, location: os.PathLike[str]) -> None:
        self.location = location

    def save(self, driver: WebDriver):
        cookies = driver.get_cookies()
        pickle.dump(cookies, file=open(self.location, "wb"))

    def load(self, driver: WebDriver, refresh: bool = True) -> bool:
        """Loads cookies into the web driver

        Args:
            driver (WebDriver): The driver to load the cookies into.
            refresh (bool, optional): If the driver should refresh after loading cookies. Defaults to True.

        Returns:
            bool: If there were cookies to load.
        """
        try:
            cookies = pickle.load(open(self.location, "rb"))
            if not cookies:
                return False
            for cookie in cookies:
                driver.add_cookie(cookie)
            if refresh:
                driver.refresh()
            return True
        except FileNotFoundError:
            return False
