from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup, element
from collections import Counter
import fileUtils
import time
import re


def extractDegree(text: str) -> int | None:
    """
    Extract a LinkedIn connection degree from a localized label.

    Args:
        - text (str): The text containing the degree label.

    Returns:
        - int | None: The extracted degree as an integer, or None if not found.
    """
    match = re.search(
        r"(?:^|[·•]\s*)(1er|2º|3er)\+?(?:\s|$)",
        text.strip(),
        re.IGNORECASE,
    )
    if not match:
        return None

    return int(match.group(1)[0])


def reverseImageMapping() -> dict[str, str]:
    """
    Create a reverse mapping of image URLs to profile IDs from the stored profiles.

    It also cleans up the profiles by removing expired image URLs and duplicates.

    Args:
        - None

    Returns:
        - dict[str, str]: A dictionary mapping image URLs to profile IDs.
    """
    allProfiles = fileUtils.getProfiles()

    # Check that there are no duplicate image URLs
    imageUrls = [v["imageUrl"] for v in allProfiles.values()]
    counts = Counter(url for url in imageUrls if url)

    for profile in allProfiles.values():
        url = profile["imageUrl"]

        if url == "":
            continue

        # Check the timestamp ?e=1794441600
        query = parse_qs(urlparse(url).query)
        timestamp = query.get("e", [None])[0]

        # Delete if the timestamp is in the past
        if int(timestamp) < int(time.time()):
            print(f"{profile['name']} has an expired image URL")
            profile["imageUrl"] = ""
            continue

        # Change image to "" for the duplicates
        if counts[url] > 1:

            print(f"{profile["name"]} has a duplicate image URL: {url}")
            profile["imageUrl"] = ""

    fileUtils.saveProfiles(allProfiles)

    reverseImage = {
        v["imageUrl"]: k for k, v in allProfiles.items() if v["imageUrl"] != ""
    }

    return reverseImage


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

    It can also obtain:
        - location
        - nCommonContacts
        - degree

    Args:
        - elements (list[element.Tag]): A list of BeautifulSoup elements containing the profile information.

    Returns:
        - dict[str, dict[str, str]]: A dictionary containing the extracted profiles.
    """
    foundProfiles = []
    profiles = fileUtils.getProfiles()

    for e in elements:

        isInvitation = bool(
            e.get("componentkey", "").startswith("invitation_manager_row_")
            or e.find(
                attrs={
                    "componentkey": lambda value: value
                    and value.startswith("invitation_manager_row_")
                }
            )
        )

        links = [e] if e.name == "a" else []
        links.extend(e.find_all("a", href=True))
        profileLink = next(
            (
                link
                for link in links
                if link.get("href")
                if "/in/" in link["href"]
                and (link.find("p") or (link.find_parent("p") and isInvitation))
            ),
            None,
        )
        if profileLink is None:
            continue

        profileParagraphs = profileLink.find_all("p")

        if isInvitation:
            name = profileLink.find("strong").get_text(" ", strip=True)
            profileDetails = [
                paragraph.get_text(" ", strip=True)
                for paragraph in e.find_all("p")
                if "quiere conectar" not in paragraph.get_text(" ", strip=True).lower()
            ]

        else:
            name = profileParagraphs[0].get_text(" ", strip=True)
            if "siguen esta página" in name.lower():
                continue

            degree = next(
                (
                    profileDegree
                    for paragraph in profileParagraphs[:2]
                    if (
                        profileDegree := extractDegree(
                            paragraph.get_text(" ", strip=True)
                        )
                    )
                    is not None
                ),
                None,
            )
            name = (
                name.replace("• 1er", "")
                .replace("• 2º", "")
                .replace("· 3er+", "")
                .strip()
            )

            profileDetails = []
            for paragraph in profileParagraphs[1:]:
                text = paragraph.get_text(" ", strip=True)
                if extractDegree(text) is None:
                    profileDetails.append(text)

        currentJob = profileDetails[0]

        profileUrl = profileLink["href"]
        image = next(
            (
                link.find(
                    "img",
                    src=lambda src: src
                    and ("profile-displayphoto" in src or "profile-framedphoto" in src),
                )
                for link in links
                if link.get("href") == profileUrl
                and link.find(
                    "img",
                    src=lambda src: src
                    and ("profile-displayphoto" in src or "profile-framedphoto" in src),
                )
            ),
            None,
        )
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

        if not isInvitation and degree is not None:
            profiles[profileID]["degree"] = degree

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
        location = (
            profileDetails[1] if not isInvitation and len(profileDetails) > 1 else ""
        )
        if location:
            profiles[profileID]["location"] = location

        commonContactsContainer = next(
            (
                container
                for container in e.find_all(["p", "span"])
                if re.search(
                    r"(?:\d[\d.,]*\s+contactos?\s+m[aá]s"
                    r"(?:\s+en\s+com[uú]n)?|contactos?\s+en\s+com[uú]n)",
                    container.get_text(" ", strip=True),
                    re.IGNORECASE,
                )
            ),
            None,
        )

        if commonContactsContainer:
            nCommonContacts = 0
            commonContactsText = commonContactsContainer.get_text(" ", strip=True)
            commonContactsMatch = re.search(
                r"\b(\d[\d.,]*)\s+contactos?\s+m[aá]s" r"(?:\s+en\s+com[uú]n)?\b",
                commonContactsText,
                re.IGNORECASE,
            )
            commonContactProfiles = {
                urlparse(link["href"]).path.strip("/")
                for link in commonContactsContainer.find_all("a", href=True)
                if urlparse(link["href"]).path.strip("/").startswith("in/")
            }
            nCommonContacts = len(commonContactProfiles)

            if commonContactsMatch:
                nCommonContacts += int(
                    commonContactsMatch.group(1).replace(".", "").replace(",", "")
                )

                # Recommendation cards render the first mutual contact as plain text
                if (
                    not commonContactProfiles
                    and commonContactsText[: commonContactsMatch.start()].strip()
                ):
                    nCommonContacts += 1
            elif re.search(
                r"\bcontactos?\s+en\s+com[uú]n\b",
                commonContactsText,
                re.IGNORECASE,
            ):
                nCommonContacts = 1

            profiles[profileID]["nCommonContacts"] = nCommonContacts

    fileUtils.saveProfiles(profiles)

    toret = {k: v for k, v in profiles.items() if k in foundProfiles}

    # Sort by name
    toret = dict(
        sorted(toret.items(), key=lambda x: fileUtils.normalizeName(x[1]["name"]))
    )

    return toret


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
    soup: BeautifulSoup, person: str = None, name: str = None
) -> dict[str, dict]:
    """
    Extract LinkedIn connections from the provided BeautifulSoup object and save them to a JSON file.

    Args:
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn connections.
        - person (str): The person's identifier in the dictionary of profiles.
        - name (str): The person's name.

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
        fileUtils.saveSecondConnections(person, name, connections)

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

    directConnections = fileUtils.getFirstConnections()

    reverseImage = reverseImageMapping()

    # Find all the https://media.licdn.com/dms/image/v2/
    extraConnections = {}
    urls = soup.find_all(
        "img",
        src=lambda x: x and x.startswith("https://media.licdn.com/dms/image/v2/"),
    )
    for url in urls:
        if url["src"] in reverseImage:
            profileBaseUrl = reverseImage[url["src"]]
            if profileBaseUrl not in directConnections and profileBaseUrl != person:
                extraConnections[profileBaseUrl] = allProfiles[profileBaseUrl]

    if extraConnections:
        previousConnections = fileUtils.getSecondConnections(person)

        previousConnections.update({k: v["name"] for k, v in extraConnections.items()})

        fileUtils.saveSecondConnections(
            person, allProfiles[person]["name"], previousConnections
        )

    return extraConnections


def scrapeMainProfile(soup: BeautifulSoup, person: str = None) -> dict:
    """
    Scrape the main profile information from the provided BeautifulSoup object.

    It will add:
        - name
        - profileUrl
        - imageUrl
        - currentJob
        - location
        - degree
        - nContacts
        - nCommonContacts

    It will also add the unix timestamp that should be used to
    not scrape the profile all the time.

    Args:
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn profile.
        - person (str): The person's identifier in the dictionary of profiles.

    Returns:
        - dict: A dictionary containing the scraped profile information.
    """
    newInfo = {}

    profileLinks = [
        link
        for link in soup.find_all("a", href=True)
        if "/in/" in link["href"] and link.find("p")
    ]
    profileLink = next(
        (
            link
            for link in profileLinks
            if person
            and urlparse(link["href"]).path.rstrip("/").split("/")[-1] == person
        ),
        profileLinks[0] if profileLinks else None,
    )

    profileParagraphs = profileLink.find_all("p")

    # Extract the name, profile URL, and image URL
    newInfo["name"] = profileParagraphs[0].get_text(" ", strip=True)
    newInfo["profileUrl"] = profileLink["href"]
    newInfo["imageUrl"] = (
        profileLink.find("img", src=True).get("src", "")
        if profileLink.find("img", src=True)
        else ""
    )

    # Extract the current job
    newInfo["currentJob"] = profileParagraphs[1].get_text(" ", strip=True)

    # Extract the location
    contactLink = soup.find(
        "a",
        href=lambda href: href and "overlay/contact-info" in href,
    )
    contactContainer = contactLink.parent.parent
    location = contactContainer.find("p")
    newInfo["location"] = location.get_text(" ", strip=True)

    # Extract the internal LinkedIn identifier
    recipientLink = soup.find(
        "a",
        href=lambda href: href and "recipient=" in href,
    )

    linkedinID = (
        parse_qs(urlparse(recipientLink["href"]).query).get("recipient", [None])[0]
        if recipientLink
        else None
    )

    componentKey = soup.find(
        attrs={"componentkey": re.compile(r"ACo[A-Za-z0-9_-]{36}")}
    )
    if componentKey:
        match = re.search(
            r"ACo[A-Za-z0-9_-]{36}",
            componentKey["componentkey"],
        )

        # The page can contain recipient links for recommended contacts, so the
        # profile card identifier is authoritative when it is available.
        linkedinID = match.group(0)

    newInfo["linkedinID"] = linkedinID

    profileText = soup.get_text(" ", strip=True)
    contactsMatch = re.search(
        r"(?<!y\s)(\d[\d.,]*)\s+contactos?\b" r"(?!\s+m[aá]s\s+en\s+com[uú]n)",
        profileText,
        re.IGNORECASE,
    )

    # Extract the degree if available. The profile header ends at the location;
    # searching beyond it includes degrees from feed and recommendation cards.
    degree = None
    for ancestor in profileLink.parents:
        paragraphs = ancestor.find_all("p")
        if location not in paragraphs or profileParagraphs[0] not in paragraphs:
            continue

        nameIndex = paragraphs.index(profileParagraphs[0])
        locationIndex = paragraphs.index(location)
        headerParagraphs = paragraphs[nameIndex:locationIndex]
        degree = next(
            (
                profileDegree
                for paragraph in headerParagraphs
                if "•" in paragraph.get_text(" ", strip=True)
                and (
                    profileDegree := extractDegree(paragraph.get_text(" ", strip=True))
                )
                is not None
            ),
            None,
        )
        if degree is None:
            degree = next(
                (
                    profileDegree
                    for paragraph in headerParagraphs
                    if (
                        profileDegree := extractDegree(
                            paragraph.get_text(" ", strip=True)
                        )
                    )
                    is not None
                ),
                None,
            )
        break

    if degree is not None:
        newInfo["degree"] = degree

    # Total number of contacts
    nContacts = (
        int(contactsMatch.group(1).replace(".", "").replace(",", ""))
        if contactsMatch
        else 0
    )
    newInfo["nContacts"] = nContacts

    # The number of common contacts
    commonContactsLink = next(
        (
            link
            for link in soup.find_all("a")
            if re.search(
                r"(?:\d[\d.,]*\s+contactos?\s+m[aá]s|contactos?)\s+en\s+com[uú]n",
                link.get_text(" ", strip=True),
                re.IGNORECASE,
            )
        ),
        None,
    )

    if commonContactsLink:
        commonContactsText = commonContactsLink.get_text(" ", strip=True)
        commonContactsMatch = re.search(
            r"\b(\d[\d.,]*)\s+contactos?\s+m[aá]s\s+en\s+com[uú]n\b",
            commonContactsText,
            re.IGNORECASE,
        )
        nCommonContacts = len(commonContactsLink.find_all("strong"))
        if commonContactsMatch:
            nCommonContacts += int(
                commonContactsMatch.group(1).replace(".", "").replace(",", "")
            )
        newInfo["nCommonContacts"] = nCommonContacts

    else:
        newInfo["nCommonContacts"] = 0

    # The timestamp
    if fileUtils.STORE_PROFILES:
        newInfo["timestamp"] = int(time.time())

    # Add extra profile information if available
    extractRecommendedPeople(soup)

    profiles = fileUtils.getProfiles()

    if person is not None and person in profiles:
        profiles[person].update(newInfo)
    elif person is not None:
        profiles[person] = newInfo

    fileUtils.saveProfiles(profiles)

    return newInfo
