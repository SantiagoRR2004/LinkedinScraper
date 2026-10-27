from selenium import webdriver
from bs4 import BeautifulSoup
import linkedinHtml
import fileUtils
import random
import time
import tqdm


def scrollToBottom(driver: webdriver.Chrome) -> None:
    """
    Scroll to the bottom of the page using JavaScript.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - None
    """
    fileUtils.waitRandomTime(1)

    # Scroll the correct container
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
        fileUtils.waitRandomTime(1)


def scrapeMainProfiles(driver: webdriver.Chrome) -> dict[str, dict]:
    """
    Scrape the main profiles of the first connections of the
    logged-in user on LinkedIn and save them to a JSON file.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - dict: A dictionary containing the scraped profile data.
    """
    profiles = fileUtils.getProfiles()
    connections = fileUtils.getFirstConnections()
    invitations = fileUtils.getInvitations()

    connectionsData = {}
    personToScrape = []

    for person in set(connections.keys()).union(set(invitations.keys())):

        if not profiles[person].get("timestamp"):
            personToScrape.append(person)

        else:
            seconds = int(time.time()) - profiles[person]["timestamp"]

            # Sample the number of random seconds from two millions
            if seconds > random.randint(0, 2 * 10**6):
                personToScrape.append(person)

    # Only scrape the profiles that need to be scraped
    for person in tqdm.tqdm(personToScrape, desc="Scraping main profiles"):

        personData = profiles[person]

        driver.get(personData["profileUrl"])
        fileUtils.waitRandomTime()

        soup = BeautifulSoup(driver.page_source, "html.parser")

        personData.update(linkedinHtml.scrapeMainProfile(soup, person))
        fileUtils.waitRandomTime()

        connectionsData[person] = personData

    return connectionsData


def obtainDirectConnections(driver: webdriver.Chrome) -> dict[str, dict]:
    """
    Obtain the direct connections of the logged-in user on LinkedIn and save them to a JSON file.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - dict: The direct connections
    """
    # Get the LinkedIn connections page
    driver.get("https://www.linkedin.com/mynetwork/invite-connect/connections/")
    scrollToBottom(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    connections = linkedinHtml.extractLinkedinConnections(soup, person=None, name=None)

    return connections


def obtainGrowingNetwork(driver: webdriver.Chrome) -> dict[str, dict]:
    """
    Obtain the growing network of the logged-in user on LinkedIn and save them to a JSON file.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - dict: The growing network.
    """
    driver.get("https://www.linkedin.com/mynetwork/grow/")
    scrollToBottom(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    profileDivs = [
        div
        for div in soup.find_all("div", attrs={"role": "listitem"})
        if div.find("a", href=lambda href: href and "/in/" in href)
    ]

    return linkedinHtml.extractProfiles(profileDivs)


def obtainInvitations(driver: webdriver.Chrome) -> dict[str, dict]:
    """
    Obtain the invitations of the logged-in user on LinkedIn and save them to a JSON file.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - dict: The profiles of the invitations.
    """
    driver.get("https://www.linkedin.com/mynetwork/invitation-manager/received/")
    scrollToBottom(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    profileDivs = soup.find_all(
        "div",
        attrs={
            "componentkey": lambda value: value
            and value.startswith("invitation_manager_row_")
        },
    )

    invitations = linkedinHtml.extractProfiles(profileDivs)

    storeInvitations = {k: v["name"] for k, v in invitations.items()}
    fileUtils.saveInvitations(storeInvitations)

    return invitations


def obtainInterpersonalFirst(driver: webdriver.Chrome) -> None:
    """
    Obtain the relationships to the first-degree connections
    of the logged-in user on LinkedIn and save them to the JSON files.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - None
    """
    directConnections = fileUtils.getFirstConnections()
    allProfiles = fileUtils.getProfiles()

    validProfiles = {}
    for k, v in allProfiles.items():
        previousConnections = fileUtils.getSecondConnections(k)

        nPreviousCommonContacts = len(
            [p for p in previousConnections if p in directConnections]
        )

        if (
            v.get("linkedinID") is not None
            and v.get("nCommonContacts", 0) > nPreviousCommonContacts
        ):
            validProfiles[k] = v

    # Sort by nCommonContacts in descending order
    validProfiles = dict(
        sorted(
            validProfiles.items(),
            key=lambda item: item[1]["nCommonContacts"],
            reverse=True,
        )
    )

    for person, personData in tqdm.tqdm(
        validProfiles.items(), desc="First-degree connections"
    ):

        # It can change by adding new connections
        previousConnections = fileUtils.getSecondConnections(person)

        nPreviousCommonContacts = len(
            [p for p in previousConnections if p in directConnections]
        )

        # Found all the common connections
        if personData.get("nCommonContacts", 0) <= nPreviousCommonContacts:
            continue

        url = (
            "https://www.linkedin.com/search/results/people/?"
            + f'network=["F"]'
            + "&"
            + f'connectionOf=["{personData["linkedinID"]}"]'
        )

        nConnections = 10
        page = 1

        while nConnections == 10:

            driver.get(url + f"&page={page}")
            fileUtils.waitRandomTime()

            soup = BeautifulSoup(driver.page_source, "html.parser")

            foundConnections = linkedinHtml.extractLinkedinConnections(
                soup, person, name=personData["name"]
            )

            nConnections = len(foundConnections)
            page += 1
            fileUtils.waitRandomTime()


def obtainInterpersonalSecond(driver: webdriver.Chrome) -> None:
    """
    Obtain the relationships to the second-degree connections
    of the logged-in user on LinkedIn and save them to the JSON files.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - None
    """
    directConnections = fileUtils.getFirstConnections()
    allProfiles = fileUtils.getProfiles()

    validProfiles = {}
    for k in directConnections.keys():
        personData = allProfiles[k]
        previousConnections = fileUtils.getSecondConnections(k)

        if personData.get("linkedinID") is not None and personData.get(
            "nContacts", 0
        ) > len(previousConnections):
            validProfiles[k] = personData

    # Sort by nContacts in ascending order
    validProfiles = dict(
        sorted(
            validProfiles.items(),
            key=lambda item: item[1]["nContacts"],
            reverse=False,
        )
    )

    for person, personData in tqdm.tqdm(
        validProfiles.items(), desc="Second-degree connections"
    ):
        previousConnections = fileUtils.getSecondConnections(person)

        # Have found all connections
        if personData.get("nContacts", 0) <= len(previousConnections):
            continue

        url = (
            "https://www.linkedin.com/search/results/people/?"
            + f'network=["S"]'
            + "&"
            + f'connectionOf=["{personData["linkedinID"]}"]'
        )

        nConnections = 10
        page = 1

        while nConnections == 10:

            driver.get(url + f"&page={page}")
            fileUtils.waitRandomTime()

            soup = BeautifulSoup(driver.page_source, "html.parser")

            foundConnections = linkedinHtml.extractLinkedinConnections(
                soup, person, name=personData["name"]
            )

            extraConnections = linkedinHtml.extractLinkedinHiddenConnections(
                soup, person
            )

            foundConnections.update(extraConnections)

            nConnections = len(foundConnections)
            page += 1
            fileUtils.waitRandomTime()


def obtainInterpersonalConnections(driver: webdriver.Chrome) -> None:
    """
    Obtain the interpersonal connections of the logged-in user on LinkedIn and save them to the
    JSON files.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - None
    """
    obtainInterpersonalFirst(driver)
    obtainInterpersonalSecond(driver)
