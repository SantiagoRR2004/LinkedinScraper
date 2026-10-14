from selenium import webdriver
from bs4 import BeautifulSoup
import linkedinHtml
import random
import time
import os


def obtainDirectConnections(driver: webdriver.Chrome) -> dict:
    """
    Obtain the direct connections of the logged-in user on LinkedIn and save them to a JSON file.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - dict: The direct connections
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))

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
    connections = linkedinHtml.extractLinkedinConnections(
        soup, os.path.join(currentDirectory, "connections.json")
    )

    for person, personData in connections.items():
        driver.get(personData["profileUrl"])
        time.sleep(2 + 2 * random.random())

        soup = BeautifulSoup(driver.page_source, "html.parser")

        personData.update(linkedinHtml.scrapeMainProfile(person, soup))
        time.sleep(2 + 2 * random.random())

    return connections
