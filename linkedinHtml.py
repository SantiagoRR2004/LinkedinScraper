from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup
import json
import re
import os


def extractLinkedinConnections(soup: BeautifulSoup, filePath: str) -> dict:
    """
    Extract LinkedIn connections from the provided BeautifulSoup object and save them to a JSON file.

    It also updates the files with all the profiles found so far.

    Args:
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn connections.
        - filePath (str): The path to the JSON file where the connections will be saved.

    Returns:
        - dict: A dictionary containing the extracted connections.
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    completeProfilesFile = os.path.join(currentDirectory, "profiles.json")

    profiles = {}
    if os.path.exists(completeProfilesFile):
        with open(completeProfilesFile, "r", encoding="utf-8") as f:
            profiles = json.load(f)

    connections = {}
    if os.path.exists(filePath):
        with open(filePath, "r", encoding="utf-8") as f:
            connections = json.load(f)
    foundConnections = []

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
        name = name.replace("• 1er", "").replace("• 2º", "").strip()

        currentJob = (
            profileParagraphs[1].get_text(" ", strip=True)
            if len(profileParagraphs) > 1
            else ""
        )
        profileUrl = profileLink["href"]
        image = div.find("img", src=True)
        imageUrl = image["src"] if image else ""

        # Get the last segment of the profile URL
        profileID = urlparse(profileUrl).path.strip("/").split("/")[1]

        # Find the internal identifier
        messageLink = next(
            (
                link
                for link in div.find_all("a", href=True)
                if "recipient=" in link["href"]
            ),
            None,
        )

        if messageLink:
            linkedinID = parse_qs(urlparse(messageLink["href"]).query).get(
                "recipient", [None]
            )[0]

        else:
            searchResults = div.find(
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

        # Connections only have the name, but it shouldn't be used
        connections[profileID] = name

        profiles.setdefault(profileID, {}).update(
            {
                "name": name,
                "profileUrl": profileUrl,
                "linkedinID": linkedinID,
                "imageUrl": imageUrl,
                "currentJob": currentJob,
            }
        )
        foundConnections.append(profileID)

    # Sort by name
    profiles = dict(sorted(profiles.items(), key=lambda x: x[1]["name"].lower()))
    connections = dict(sorted(connections.items(), key=lambda x: x[1].lower()))

    with open(filePath, "w", encoding="utf-8") as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(completeProfilesFile, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {k: v for k, v in profiles.items() if k in foundConnections}


def scrapeMainProfile(person, soup: BeautifulSoup) -> dict:
    """
    Scrape the main profile information from the provided BeautifulSoup object.

    Args:
        - person (str): The person's identifier in the dictionary of profiles.
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn profile.

    Returns:
        - dict: A dictionary containing the scraped profile information.
    """
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    completeProfilesFile = os.path.join(currentDirectory, "profiles.json")

    profiles = {}
    if os.path.exists(completeProfilesFile):
        with open(completeProfilesFile, "r", encoding="utf-8") as f:
            profiles: dict[str, dict] = json.load(f)

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

    profiles[person].update(newInfo)
    with open(completeProfilesFile, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return newInfo
