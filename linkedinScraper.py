from selenium import webdriver
from bs4 import BeautifulSoup
import linkedinHtml
import fileUtils


def obtainDirectConnections(driver: webdriver.Chrome) -> dict[str:dict]:
    """
    Obtain the direct connections of the logged-in user on LinkedIn and save them to a JSON file.

    Args:
        - driver (webdriver.Chrome): A Selenium WebDriver instance for Chrome.

    Returns:
        - dict: The direct connections
    """
    # Get the LinkedIn connections page
    driver.get("https://www.linkedin.com/mynetwork/invite-connect/connections/")
    fileUtils.waitRandomTime(1)

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
        fileUtils.waitRandomTime(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    connections = linkedinHtml.extractLinkedinConnections(soup, person=None)

    for person, personData in connections.items():
        driver.get(personData["profileUrl"])
        fileUtils.waitRandomTime()

        soup = BeautifulSoup(driver.page_source, "html.parser")

        personData.update(linkedinHtml.scrapeMainProfile(soup, person))
        fileUtils.waitRandomTime()

    return connections


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

        # Need to have common contacts
        if personData.get("hasCommonContacts") and not any(
            p for p in previousConnections if p in directConnections
        ):
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
