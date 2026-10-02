from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup
import subprocess
import random
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


currentDirectory = os.path.dirname(os.path.abspath(__file__))
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
    f"google-chrome --user-data-dir={dst} --remote-debugging-port=9222", shell=True
)

time.sleep(2)


# Check that the browser has a remote debugging port open
output = subprocess.check_output("curl http://127.0.0.1:9222/json/version", shell=True)
json.loads(output.decode("utf-8"))

# Connect to the browser using Selenium
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)

# Get the LinkedIn connections page
driver.get("https://www.linkedin.com/mynetwork/invite-connect/connections/")
time.sleep(2 + random.random())


# Scroll the container that actually owns the connections list
scrollScript = """
const root = document.scrollingElement;
const candidates = [root, ...document.querySelectorAll('*')]
    .filter((element, index, elements) => element && elements.indexOf(element) === index)
    .filter(element => {
        const style = getComputedStyle(element);
        return element.scrollHeight > element.clientHeight &&
            (element === root || style.overflowY === 'auto' || style.overflowY === 'scroll');
    })
    .sort((left, right) => right.scrollHeight - left.scrollHeight);
const target = candidates[0] || root;
target.scrollTo(0, target.scrollHeight);
return {
    height: target.scrollHeight,
    top: target.scrollTop,
    tag: target.tagName,
    className: target.className
};
"""

lastHeight = -1
newHeight = 0

while lastHeight != newHeight:
    lastHeight = newHeight
    newHeight = driver.execute_script(scrollScript)["height"]
    time.sleep(2 + random.random())


soup = BeautifulSoup(driver.page_source, "html.parser")


# The divs with the connections
connectionsDivs = soup.find_all(
    "div",
    attrs={"componentkey": lambda value: value and value.startswith("ConnectionCard_")},
)

directConnections = {}

for div in connectionsDivs:
    profileLink = next(
        (
            link
            for link in div.find_all("a", href=True)
            if "/in/" in link["href"] and link.find("p")
        ),
        None,
    )
    profileParagraphs = profileLink.find_all("p")

    name = profileParagraphs[0].get_text(" ", strip=True)
    currentJob = (
        profileParagraphs[1].get_text(" ", strip=True)
        if len(profileParagraphs) > 1
        else ""
    )
    profileUrl = profileLink["href"]
    image = div.find("img", src=True)
    imageUrl = image["src"] if image else ""

    # Get the last segment of the profile URL
    profileId = profileUrl.split("/")[-2]

    directConnections[profileId] = {
        "name": name,
        "profileUrl": profileUrl,
        "imageUrl": imageUrl,
        "currentJob": currentJob,
    }


# Sort the connections by name
directConnections = dict(
    sorted(directConnections.items(), key=lambda x: x[1]["name"].lower())
)


with open(
    os.path.join(currentDirectory, "connections.json"), "w", encoding="utf-8"
) as f:
    json.dump(directConnections, f, indent=2, ensure_ascii=False)
    f.write("\n")
