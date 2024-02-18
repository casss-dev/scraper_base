from enum import Enum
import time
import os

from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType


class WebDriverBuilder:
    """A builder for conveniently creating web drivers

    Note:
    webdriver_manager saves drivers in the following path:
    $HOME/.wdm/drivers/chromedriver/mac64/120.0.6099.109/chromedriver-mac-arm64/chromedriver
    """

    class RemoteDriverTimeout(Exception):
        """
        Raised when building a remote web driver reaches its max retry count
        """

        pass

    class DriverType(Enum):
        Chrome = "chrome"
        Chromium = "chromium"
        Standalone = "standalone"

    STANDALONE_LOCAL_URL = "http://localhost:4444"

    def __init__(
        self,
        remote_port: int = 4444,
        show_browser: bool = False,
        in_container: bool = False,
        implicit_wait_time: int = 10,
    ) -> None:
        self.remote_port = remote_port
        self.show_browser = show_browser
        self.container = in_container
        self.implicit_wait_time = implicit_wait_time

    def build(self, driver_type: DriverType) -> WebDriver:
        """A convenience function to build a driver of the specified type

        Args:
            driver_type (DriverType): The type of driver to build

        Raises:
            WebDriverBuilder.RemoteDriverTimeout: Occurs when a remote driver reaches its max
            connection retry count

        Returns:
            WebDriver: A web driver for scraping
        """
        match driver_type:
            case WebDriverBuilder.DriverType.Chrome:
                return self.build_chrome(self.chrome_options)
            case WebDriverBuilder.DriverType.Chromium:
                return self.build_chrome(
                    self.chrome_options, chrome_type=ChromeType.CHROMIUM
                )
            case WebDriverBuilder.DriverType.Standalone:
                if self.show_browser:
                    standalone_url = "http://localhost:7900/?autoconnect=1&resize=scale&password=secret"
                    os.system(f"open '{standalone_url}'")
                driver = self.build_remote(url=self.STANDALONE_LOCAL_URL)
                if not driver:
                    raise WebDriverBuilder.RemoteDriverTimeout
                return driver

    @property
    def chrome_options(self) -> webdriver.ChromeOptions:
        opts = webdriver.ChromeOptions()
        if not self.show_browser:
            opts.add_argument("--headless")
        if self.container:
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
        return opts

    def build_chrome(
        self, options: webdriver.ChromeOptions, chrome_type: str = ChromeType.GOOGLE
    ) -> WebDriver:
        """Builds an instance of a chrome browser.

        Args:
            chrome_type (str, optional): The type of chrome browser. Defaults to ChromeType.GOOGLE.

        Returns:
            WebDriver: A chrome web driver
        """
        path = ChromeDriverManager(chrome_type=chrome_type).install()
        service = Service(executable_path=path)
        driver = webdriver.Chrome(options=options, service=service)
        self._config_driver(driver)
        return driver

    def build_remote(
        self, url: str, retry_count: int = 3, retry_delay: int = 5
    ) -> WebDriver | None:
        """Builds a web driver for connecting to a remote browser.

        Args:
            url (str | None, optional): The url to connect to. Defaults to STANDALONE_LOCAL_URL
            retry_count (int): The maximum number of times to attempt to connect to the remote url
            retry_delay (int): The delay between retries

        Returns:
            WebDriver: A remote web driver
        """
        if retry_count <= 0:
            return None
        try:
            driver = webdriver.Remote(url)
        except:
            driver = None
        if not driver:
            time.sleep(retry_count)
            return self.build_remote(url, retry_count=retry_count - 1)
        self._config_driver(driver)
        return driver

    def _config_driver(self, driver: WebDriver):
        if self.implicit_wait_time > 0:
            driver.implicitly_wait(self.implicit_wait_time)