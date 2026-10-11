from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup
import driverUtils
import random
import json
import time
import os

currentDirectory = os.path.dirname(os.path.abspath(__file__))
driver = driverUtils.createDriver()

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
    profileID = profileUrl.split("/")[-2]

    # Find the internal identifier
    messageLink = next(
        (link for link in div.find_all("a", href=True) if "recipient=" in link["href"]),
        None,
    )
    linkedinID = parse_qs(urlparse(messageLink["href"]).query).get("recipient", [None])[
        0
    ]

    directConnections[profileID] = {
        "name": name,
        "profileUrl": profileUrl,
        "linkedinID": linkedinID,
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


pass
