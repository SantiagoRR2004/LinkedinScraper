from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup
import json
import os


def extractLinkedinConnections(soup: BeautifulSoup, filePath: str) -> dict:
    """
    Extract LinkedIn connections from the provided BeautifulSoup object and save them to a JSON file.

    Args:
        - soup (BeautifulSoup): A BeautifulSoup object containing the HTML of the LinkedIn connections.
        - filePath (str): The path to the JSON file where the connections will be saved.

    Returns:
        - dict: A dictionary containing the extracted connections.
    """
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

    connections = {}
    if os.path.exists(filePath):
        with open(filePath, "r", encoding="utf-8") as f:
            connections = json.load(f)
    foundConnections = []

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

        connections.setdefault(profileID, {}).update(
            {
                "name": name,
                "profileUrl": profileUrl,
                "linkedinID": linkedinID,
                "imageUrl": imageUrl,
                "currentJob": currentJob,
            }
        )
        foundConnections.append(profileID)

    # Sort the connections by name
    connections = dict(sorted(connections.items(), key=lambda x: x[1]["name"].lower()))

    with open(filePath, "w", encoding="utf-8") as f:
        json.dump(connections, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return {k: v for k, v in connections.items() if k in foundConnections}
