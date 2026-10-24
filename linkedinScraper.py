from selenium import webdriver
from bs4 import BeautifulSoup
import linkedinHtml
import fileUtils


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

    connectionsData = {}
    for person in connections:

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
    connections = linkedinHtml.extractLinkedinConnections(soup, person=None)

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


def obtainInterpersonalConnections(driver: webdriver.Chrome) -> None:
    """
    Obtain the interpersonal connections of the logged-in user on LinkedIn and save them to the
    JSON files.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - None
    """
    directConnections = fileUtils.getFirstConnections()
    allProfiles = fileUtils.getProfiles()

    reverseImage = {v["imageUrl"]: k for k, v in allProfiles.items()}

    for person, personData in allProfiles.items():

        if personData.get("linkedinID") is None:
            continue

        previousConnections = fileUtils.getSecondConnections(person)

        typesOfConnections = []

        nPreviousCommonContacts = len(
            p for p in previousConnections if p in directConnections
        )

        # Not found all the common connections yet
        if personData.get("nCommonContacts", 0) > nPreviousCommonContacts:
            typesOfConnections.append("F")

        if (
            personData.get("nContacts", 0)
            > len(previousConnections)  # Not found all yet
            and person
            in directConnections  # Only find second-degree connections for direct connections
        ):
            typesOfConnections.append("S")

        for n in typesOfConnections:

            url = (
                "https://www.linkedin.com/search/results/people/?"
                + f'network=["{n}"]'
                + "&"
                + f'connectionOf=["{personData["linkedinID"]}"]'
            )

            nConnections = 10
            page = 1

            while nConnections == 10:

                driver.get(url + f"&page={page}")
                fileUtils.waitRandomTime()

                soup = BeautifulSoup(driver.page_source, "html.parser")

                foundConnections = linkedinHtml.extractLinkedinConnections(soup, person)

                # Only find extra connections with Second-degree
                if n == "S":

                    # Find all the https://media.licdn.com/dms/image/v2/
                    extraConnections = {}
                    urls = soup.find_all(
                        "img",
                        src=lambda x: x
                        and x.startswith("https://media.licdn.com/dms/image/v2/"),
                    )
                    for url in urls:
                        if url["src"] in reverseImage:
                            profileBaseUrl = reverseImage[url["src"]]
                            if (
                                profileBaseUrl not in foundConnections
                                and profileBaseUrl not in directConnections
                                and profileBaseUrl != person
                            ):
                                extraConnections[profileBaseUrl] = allProfiles[
                                    profileBaseUrl
                                ]

                    foundConnections.update(extraConnections)

                    if extraConnections:
                        previousConnections = fileUtils.getSecondConnections(person)

                        previousConnections.update(
                            {k: v["name"] for k, v in extraConnections.items()}
                        )

                        fileUtils.saveSecondConnections(person, previousConnections)

                nConnections = len(foundConnections)
                page += 1
                fileUtils.waitRandomTime()
