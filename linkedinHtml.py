from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup, element
import fileUtils
import re


def extractProfiles(elements: list[element.Tag]) -> dict[str, dict]:
    """
    Extract the profiles from the provided list of BeautifulSoup elements.

    It also updates the file with all the profiles found so far.

    This will always obtain:
        - name
        - profileUrl (can be empty)
        - imageUrl
        - currentJob

    It can obtain the internal LinkedIn identifier if:
        - mynetwork/invite-connect/connections/
        - search/results/people/

    It can also obtain the location.

    Args:
        - elements (list[element.Tag]): A list of BeautifulSoup elements containing the profile information.

    Returns:
        - dict[str, dict[str, str]]: A dictionary containing the extracted profiles.
    """
    foundProfiles = []
    profiles = fileUtils.getProfiles()

    for e in elements:

        links = [e] if e.name == "a" else []
        links.extend(e.find_all("a", href=True))
        profileLink = next(
            (
                link
                for link in links
                if link.get("href")
                if "/in/" in link["href"] and link.find("p")
            ),
            None,
        )
        if profileLink is None:
            continue

        profileParagraphs = profileLink.find_all("p")

        name = profileParagraphs[0].get_text(" ", strip=True)
        if "siguen esta página" in name.lower():
            continue

        name = (
            name.replace("• 1er", "").replace("• 2º", "").replace("· 3er+", "").strip()
        )

        profileDetails = []
        for paragraph in profileParagraphs[1:]:
            text = paragraph.get_text(" ", strip=True)
            if not re.fullmatch(r"[•·]\s*\d+(?:er|º)\+?", text):
                profileDetails.append(text)

        currentJob = profileDetails[0]

        profileUrl = profileLink["href"]
        image = e.find("img", src=True)
        imageUrl = image["src"] if image else ""

        # Get the last segment of the profile URL
        pathParts = urlparse(profileUrl).path.strip("/").split("/")
        if len(pathParts) != 2 or pathParts[0] != "in":
            continue
        profileID = pathParts[1]

        # Find the internal identifier
        messageLink = next(
            (
                link
                for link in e.find_all("a", href=True)
                if "recipient=" in link["href"]
            ),
            None,
        )

        foundProfiles.append(profileID)
        profiles.setdefault(profileID, {}).update(
            {
                "name": name,
                "profileUrl": profileUrl,
                "imageUrl": imageUrl,
                "currentJob": currentJob,
            }
        )

        # Find optional internal LinkedIn identifier
        if messageLink:
            linkedinID = parse_qs(urlparse(messageLink["href"]).query).get(
                "recipient", [None]
            )[0]

        else:
            searchResults = e.find(
                attrs={
                    "componentkey": lambda value: value
                    and value.startswith("SearchResultsACoAA")
                }
            )
            linkedinID = (
                searchResults["componentkey"][len("SearchResults") :]
                if searchResults
                else None
            )

        if linkedinID:
            profiles[profileID]["linkedinID"] = linkedinID

        # Find the location if available
        location = profileDetails[1] if len(profileDetails) > 1 else ""
        if location:
            profiles[profileID]["location"] = location

    fileUtils.saveProfiles(profiles)

    return {k: v for k, v in profiles.items() if k in foundProfiles}


def extractRecommendedPeople(soup: BeautifulSoup) -> dict[str, dict]:
    """
    Extract the people shown in the profile page's recommendation section.

    LinkedIn renders the profile card as an anchor containing several paragraphs
    and also nests a second anchor around the name. The profile URL is therefore
    used as the deduplication key.
    """
    sections = []
    seenSections = set()

    for heading in soup.find_all(["h2", "h3"]):
        section = heading.find_parent("section")
        if (
            section
            and id(section) not in seenSections
            and re.search(
                r"(m[aá]s perfiles para ti|gente que podr[ií]as conocer|"
                r"personas que quiz[aá] puedas conocer|people you may know|"
                r"explorar perfiles premium|explore premium profiles)",
                heading.get_text(" ", strip=True),
                re.IGNORECASE,
            )
        ):
            sections.append(section)
            seenSections.add(id(section))

    profileLinks = [
        link for section in sections for link in section.find_all("a", href=True)
    ]

    return extractProfiles(profileLinks)


def extractLinkedinConnections(
    soup: BeautifulSoup, person: str = None
) -> dict[str, dict]:
    """
    Extract LinkedIn connections from the provided BeautifulSoup object and save them to a JSON file.

    Args:
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn connections.
        - person (str): The person's identifier in the dictionary of profiles.

    Returns:
        - dict: A dictionary containing the extracted connections.
    """
    if person is None:
        connections = fileUtils.getFirstConnections()
    else:
        connections = fileUtils.getSecondConnections(person)

    # The divs with the connections (mynetwork/invite-connect/connections/)
    connectionsDivs = soup.find_all(
        "div",
        attrs={
            "componentkey": lambda value: value and value.startswith("ConnectionCard_")
        },
    )

    # Second way to find the divs (search/results/people/)
    if not connectionsDivs:
        connectionsDivs = [
            div
            for div in soup.find_all("div", attrs={"role": "listitem"})
            if div.find("a", href=lambda href: href and "/in/" in href)
            and (
                div.find(
                    "a",
                    href=lambda href: href and "recipient=" in href,
                )
                or div.find(
                    "a",
                    attrs={
                        "componentkey": lambda value: value
                        and value.startswith("ConnectButtonstate:")
                    },
                )
            )
        ]

    # The profiles that were found
    profiles = extractProfiles(connectionsDivs)

    connections.update({k: v["name"] for k, v in profiles.items()})

    if person is None:
        fileUtils.saveFirstConnections(connections)
    else:
        fileUtils.saveSecondConnections(person, connections)

    return profiles


def extractLinkedinHiddenConnections(
    soup: BeautifulSoup, person: str = None
) -> dict[str, dict]:
    """
    Extract LinkedIn connections from the provided BeautifulSoup object and save them to a JSON file.

    Args:
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn connections
        - person (str): The person's identifier in the dictionary of profiles.

    Returns:
        - dict: A dictionary containing the extracted connections.
    """
    allProfiles = fileUtils.getProfiles()

    foundConnections = fileUtils.getSecondConnections(person)
    directConnections = fileUtils.getFirstConnections()

    reverseImage = {v["imageUrl"]: k for k, v in allProfiles.items()}

    # Find all the https://media.licdn.com/dms/image/v2/
    extraConnections = {}
    urls = soup.find_all(
        "img",
        src=lambda x: x and x.startswith("https://media.licdn.com/dms/image/v2/"),
    )
    for url in urls:
        if url["src"] in reverseImage:
            profileBaseUrl = reverseImage[url["src"]]
            if (
                profileBaseUrl not in foundConnections
                and profileBaseUrl not in directConnections
                and profileBaseUrl != person
            ):
                extraConnections[profileBaseUrl] = allProfiles[profileBaseUrl]

    foundConnections.update(extraConnections)

    if extraConnections:
        previousConnections = fileUtils.getSecondConnections(person)

        previousConnections.update({k: v["name"] for k, v in extraConnections.items()})

        fileUtils.saveSecondConnections(person, previousConnections)


def scrapeMainProfile(person, soup: BeautifulSoup) -> dict:
    """
    Scrape the main profile information from the provided BeautifulSoup object.

    Args:
        - person (str): The person's identifier in the dictionary of profiles.
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn profile.

    Returns:
        - dict: A dictionary containing the scraped profile information.
    """
    profileText = soup.get_text(" ", strip=True)
    contactsMatch = re.search(
        r"(?<!y\s)(\d[\d.,]*)\s+contactos?\b" r"(?!\s+m[aá]s\s+en\s+com[uú]n)",
        profileText,
        re.IGNORECASE,
    )

    nContacts = (
        int(contactsMatch.group(1).replace(".", "").replace(",", ""))
        if contactsMatch
        else 0
    )
    hasCommonContacts = bool(
        re.search(
            r"\d[\d.,]*\s+contactos?\s+m[aá]s\s+en\s+com[uú]n",
            profileText,
            re.IGNORECASE,
        )
    )
    newInfo = {"nContacts": nContacts, "hasCommonContacts": hasCommonContacts}

    # Add extra profile information if available
    extractRecommendedPeople(soup)

    profiles = fileUtils.getProfiles()
    profiles[person].update(newInfo)
    fileUtils.saveProfiles(profiles)

    return newInfo
