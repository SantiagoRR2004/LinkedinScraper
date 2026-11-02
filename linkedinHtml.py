from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup, element
from collections import Counter
import fileUtils
import json
import time
import re

CREATE_NEW_TESTS = True
EXTRACT_PROFILES_PATH = "tests/extractProfiles"
SCRAPE_MAIN_PROFILE_PATH = "tests/scrapeMainProfile"


def normalizeProfileUrl(profileUrl: str) -> str:
    """
    Remove a trailing language segment from a LinkedIn profile URL.

    LinkedIn can render the same profile as ``/in/<profile>/<language>/``.
    The language is presentation-specific and must not become part of the
    stored profile URL.

    Args:
        - profileUrl (str): The LinkedIn profile URL to normalize.

    Returns:
        - str: The normalized LinkedIn profile URL.
    """
    parsedUrl = urlparse(profileUrl)
    pathParts = parsedUrl.path.strip("/").split("/")

    if (
        len(pathParts) == 3
        and pathParts[0] == "in"
        and re.fullmatch(r"[a-z]{2}(?:-[a-z]{2})?", pathParts[2], re.IGNORECASE)
    ):
        normalizedPath = "/" + "/".join(pathParts[:2])
        if parsedUrl.path.endswith("/"):
            normalizedPath += "/"
        return parsedUrl._replace(path=normalizedPath).geturl()

    return profileUrl


def extractImageUrls(images: list[element.Tag]) -> list[str]:
    """
    Extract unique image sources and responsive source-set entries.

    Args:
        - images (list[element.Tag]): A list of BeautifulSoup image elements.

    Returns:
        - list[str]: A sorted list of unique image URLs.
    """
    imageUrls = set()

    for image in images:

        if image.get("src"):
            imageUrls.add(image["src"])

        imageUrls.update(
            source.split()[0]
            for source in image.get("srcset", "").split(",")
            if source.strip()
        )

    return sorted(imageUrls)


def extractDegree(text: str) -> int | None:
    """
    Extract a LinkedIn connection degree from a localized label.

    Args:
        - text (str): The text containing the degree label.

    Returns:
        - int | None: The extracted degree as an integer, or None if not found.
    """
    match = re.search(
        r"(?:^|[·•]\s*)(1er|2º|3er)\+?$",
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
    imageUrls = [
        imageUrl
        for profile in allProfiles.values()
        for imageUrl in profile["imageUrls"]
    ]
    counts = Counter(url for url in imageUrls if url)

    for profile in allProfiles.values():
        urls = profile["imageUrls"]
        validUrls = []

        for url in urls:

            # Check the timestamp ?e=##############
            query = parse_qs(urlparse(url).query)
            timestamp = query.get("e", [None])[0]

            # Delete if the timestamp is in the past
            if timestamp is not None and int(timestamp) < int(time.time()):
                print(f"{profile['name']} has an expired image URL")
                continue

            # Delete if the URL is a duplicate
            if counts[url] > 1:
                print(f"{profile['name']} has a duplicate image URL: {url}")
                continue

            validUrls.append(url)

        profile["imageUrls"] = validUrls

    fileUtils.saveProfiles(allProfiles)

    reverseImage = {
        imageUrl: profileId
        for profileId, profile in allProfiles.items()
        for imageUrl in profile["imageUrls"]
    }

    return reverseImage


def extractnCommonContacts(
    commonContactsContainer: element.Tag, countStrong: bool = False
) -> int:
    """
    Extract the number of common contacts from the provided BeautifulSoup element.

    Args:
        - commonContactsContainer (element.Tag): A BeautifulSoup element containing the common contacts information.
        - countStrong (bool): Whether to count the number of <strong> tags as common
            contacts. Defaults to False.

    Returns:
        - int: The number of common contacts.
    """
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
    nCommonContacts = (
        len(commonContactsContainer.find_all("strong"))
        if countStrong
        else len(commonContactProfiles)
    )

    if commonContactsMatch:
        nCommonContacts += int(
            commonContactsMatch.group(1).replace(".", "").replace(",", "")
        )

        # Recommendation cards render the first mutual contact as plain text
        if (
            not countStrong
            and not commonContactProfiles
            and commonContactsText[: commonContactsMatch.start()].strip()
        ):
            nCommonContacts += 1
    elif (
        re.search(
            r"\bcontactos?\s+en\s+com[uú]n\b",
            commonContactsText,
            re.IGNORECASE,
        )
        and not countStrong
    ):
        nCommonContacts = 1

    return nCommonContacts


def getnCommonContacts(
    commonContactsContainer: element.Tag,
    person: str,
    countStrong: bool = False,
    commonContactsImagesContainer: element.Tag | None = None,
) -> int:
    """
    Extract the number of common contacts from the provided BeautifulSoup element.

    Args:
        - commonContactsContainer (element.Tag): A BeautifulSoup element containing the common contacts information.
        - person (str): The person's identifier in the dictionary of profiles.
        - countStrong (bool): Whether to count the number of <strong> tags as common contacts. Defaults to False.
        - commonContactsImagesContainer (element.Tag | None): An optional element
            containing the common contact images.

    Returns:
        - int: The number of common contacts.
    """
    nCommonContacts = extractnCommonContacts(commonContactsContainer, countStrong)
    imagesContainer = commonContactsImagesContainer or commonContactsContainer
    connectionsImages = [image.get("src") for image in imagesContainer.find_all("img")]

    assert (
        len(connectionsImages) <= nCommonContacts
    ), f"Found {len(connectionsImages)} images but {nCommonContacts} common contacts"

    reverseImages = reverseImageMapping()

    connectionsFound = [
        reverseImages[image] for image in connectionsImages if image in reverseImages
    ]

    fileUtils.saveIncompleteConnections(person, connectionsFound)

    return nCommonContacts


def extractProfiles(elements: list[element.Tag]) -> dict[str, dict]:
    """
    Extract the profiles from the provided list of BeautifulSoup elements.

    It also updates the file with all the profiles found so far.

    This will always obtain:
        - name
        - profileUrl
        - imageUrls (can be empty)

    It obtains currentJob when the profile includes a current job.

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

        newInfo = {}

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

        profileUrl = normalizeProfileUrl(profileLink["href"])
        newInfo["profileUrl"] = profileUrl

        # Get the last segment of the profile URL
        pathParts = urlparse(profileUrl).path.strip("/").split("/")
        if len(pathParts) != 2 or pathParts[0] != "in":
            continue
        profileID = pathParts[1]
        foundProfiles.append(profileID)

        if CREATE_NEW_TESTS:
            currentTime = int(time.time())
            file = f"{EXTRACT_PROFILES_PATH}/{currentTime}_{profileID}.html"
            with open(file, "w", encoding="utf-8") as f:
                f.write(e.prettify())

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

        newInfo["name"] = name

        if profileDetails:
            newInfo["currentJob"] = profileDetails[0]

        profileImages = []
        for link in links:
            if normalizeProfileUrl(link.get("href", "")) != profileUrl:
                continue

            profileElements = link.find_all(["img", "p"])
            firstParagraphIndex = next(
                (
                    index
                    for index, element in enumerate(profileElements)
                    if element.name == "p"
                ),
                len(profileElements),
            )
            profileImages.extend(
                image
                for index, image in enumerate(profileElements)
                if index < firstParagraphIndex
                and image.name == "img"
                and image.get("src")
                and (
                    "profile-displayphoto" in image["src"]
                    or "profile-framedphoto" in image["src"]
                )
            )
        framedProfileImages = [
            image
            for image in profileImages
            if "profile-framedphoto" in image.get("src", "")
        ]
        imageUrls = extractImageUrls(
            framedProfileImages[:1] if framedProfileImages else profileImages[:1]
        )
        newInfo["imageUrls"] = imageUrls

        # Find the internal identifier
        messageLink = next(
            (
                link
                for link in e.find_all("a", href=True)
                if "recipient=" in link["href"]
            ),
            None,
        )

        if not isInvitation and degree is not None:
            newInfo["degree"] = degree

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
            newInfo["linkedinID"] = linkedinID

        # Find the location if available
        location = (
            profileDetails[1] if not isInvitation and len(profileDetails) > 1 else ""
        )
        if location:
            newInfo["location"] = location

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

            nCommonContacts = extractnCommonContacts(commonContactsContainer)
            commonContactsImagesContainer = next(
                (
                    ancestor
                    for ancestor in commonContactsContainer.parents
                    if len(ancestor.find_all("img")) <= nCommonContacts
                    and ancestor.find("img")
                ),
                None,
            )

            newInfo["nCommonContacts"] = getnCommonContacts(
                commonContactsContainer,
                person=profileID,
                commonContactsImagesContainer=commonContactsImagesContainer,
            )

        # Save if needed
        if CREATE_NEW_TESTS:
            file = f"{EXTRACT_PROFILES_PATH}/{currentTime}_{profileID}.json"
            with open(file, "w", encoding="utf-8") as f:
                json.dump({profileID: newInfo}, f, ensure_ascii=False, indent=2)
                f.write("\n")

        # Update with newInfo (imageUrls are special)
        profiles.setdefault(profileID, {})

        if profiles[profileID].get("imageUrls"):
            allImages = profiles[profileID]["imageUrls"]
            allImages += newInfo["imageUrls"]
            profiles[profileID]["imageUrls"] = list(set(allImages))

        else:
            profiles[profileID]["imageUrls"] = newInfo["imageUrls"]

        del newInfo["imageUrls"]
        profiles[profileID].update(newInfo)

    fileUtils.saveProfiles(profiles)
    reverseImageMapping()

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
                or div.find(
                    "button",
                    attrs={
                        "aria-label": lambda value: value
                        and re.search(r"\b(?:follow|seguir)\b", value, re.IGNORECASE)
                    },
                )
                or div.find(
                    "button",
                    attrs={
                        "aria-label": lambda value: value
                        and re.search(r"\b(?:accept|aceptar)\b", value, re.IGNORECASE)
                    },
                )
            )
        ]

    # The profiles that were found
    profiles = extractProfiles(connectionsDivs)

    connections.update({k: v["name"] for k, v in profiles.items()})

    if fileUtils.STORE_PROFILES and person is not None:
        # Update with connection timestamp
        timestamp = int(time.time())

        allProfiles = fileUtils.getProfiles()
        allProfiles[person]["timestampFirst"] = timestamp

        fileUtils.saveProfiles(allProfiles)

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
    reverseImage = reverseImageMapping()
    allProfiles = fileUtils.getProfiles()
    directConnections = fileUtils.getFirstConnections()

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

    if fileUtils.STORE_PROFILES and person is not None:
        # Update with connection timestamp
        timestamp = int(time.time())

        allProfiles[person]["timestampSecond"] = timestamp

        fileUtils.saveProfiles(allProfiles)

    return extraConnections


def scrapeMainProfile(soup: BeautifulSoup, person: str = None) -> dict:
    """
    Scrape the main profile information from the provided BeautifulSoup object.

    It will add:
        - name
        - profileUrl
        - imageUrls
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

    if CREATE_NEW_TESTS and person is not None:
        currentTime = int(time.time())
        file = f"{SCRAPE_MAIN_PROFILE_PATH}/{currentTime}_{person}.html"
        with open(file, "w", encoding="utf-8") as f:
            f.write(soup.prettify())

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
            and urlparse(normalizeProfileUrl(link["href"]))
            .path.rstrip("/")
            .split("/")[-1]
            == person
        ),
        profileLinks[0] if profileLinks else None,
    )

    profileParagraphs = profileLink.find_all("p")

    # Extract the name, profile URL, and image URL
    newInfo["name"] = profileParagraphs[0].get_text(" ", strip=True)
    newInfo["profileUrl"] = normalizeProfileUrl(profileLink["href"])
    profilePath = urlparse(newInfo["profileUrl"]).path.rstrip("/")
    topcardLink = soup.find(
        "a",
        attrs={"componentkey": "topcard-logo-image-referencekey"},
        href=True,
    )
    profileImageLinks = [profileLink]
    if (
        topcardLink
        and urlparse(normalizeProfileUrl(topcardLink["href"])).path.rstrip("/")
        == profilePath
    ):
        profileImageLinks.append(topcardLink)

    newInfo["imageUrls"] = extractImageUrls(
        [
            image
            for link in profileImageLinks
            for image in link.find_all(
                "img",
                src=lambda src: src
                and ("profile-displayphoto" in src or "profile-framedphoto" in src),
            )
        ]
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
    if contactsMatch:
        nContacts = int(contactsMatch.group(1).replace(".", "").replace(",", ""))
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
        newInfo["nCommonContacts"] = getnCommonContacts(
            commonContactsLink, person=person, countStrong=True
        )

    if CREATE_NEW_TESTS and person is not None:
        file = f"{SCRAPE_MAIN_PROFILE_PATH}/{currentTime}_{person}.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump(newInfo, f, ensure_ascii=False, indent=2)
            f.write("\n")

    # The timestamp
    if fileUtils.STORE_PROFILES:
        newInfo["timestamp"] = int(time.time())

    # Add extra profile information if available
    extractRecommendedPeople(soup)

    profiles = fileUtils.getProfiles()

    if person is not None:
        profiles.setdefault(person, {})

        # Keep all image URLs found so far
        if profiles[person].get("imageUrls"):
            allImages = profiles[person]["imageUrls"]
            allImages += newInfo["imageUrls"]
            profiles[person]["imageUrls"] = list(set(allImages))

        else:
            profiles[person]["imageUrls"] = newInfo["imageUrls"]

        del newInfo["imageUrls"]
        profiles[person].update(newInfo)

    fileUtils.saveProfiles(profiles)

    return newInfo
