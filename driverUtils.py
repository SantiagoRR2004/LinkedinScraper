from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import subprocess
import shutil
import json
import time
import os


def ignoreChromeSingletons(directory: str, names: list[str]) -> list[str]:
    """
    Ignore the Chrome singleton files when copying the user data directory.

    Args:
        - directory (str): The directory being copied.
        - names (list[str]): The names of the files in the directory.

    Returns:
        - list[str]: The names of the files to ignore.
    """
    return {name for name in names if name.startswith("Singleton")}


def createDriver() -> webdriver.Chrome:
    """
    Create a Selenium WebDriver instance for Chrome with remote debugging enabled.

    Args:
        - None

    Returns:
        - webdriver.Chrome: A Selenium WebDriver instance for Chrome.
    """
    src = os.path.expanduser("~/.config/google-chrome")
    dst = os.path.expanduser("~/.config/google-chrome-debug")

    shutil.copytree(
        src,
        dst,
        copy_function=shutil.copy2,
        dirs_exist_ok=True,
        ignore=ignoreChromeSingletons,
    )

    # Open the browser by terminal
    subprocess.Popen(
        f"google-chrome --user-data-dir={dst} --remote-debugging-port=9222",
        shell=True,
    )

    time.sleep(2)

    # Check that the browser has a remote debugging port open
    output = subprocess.check_output(
        f"curl http://127.0.0.1:9222/json/version", shell=True
    )
    json.loads(output.decode("utf-8"))

    # Connect to the browser using Selenium
    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:9222")

    return webdriver.Chrome(options=options)
