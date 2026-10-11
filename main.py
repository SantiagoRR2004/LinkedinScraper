import firstConnections
import driverUtils
import json
import os

from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse
import random
import time

if __name__ == "__main__":
    driver = driverUtils.createDriver()
    directConnections = firstConnections.obtainDirectConnections(driver)

    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    peopleDirectory = os.path.join(currentDirectory, "connections")
    os.makedirs(peopleDirectory, exist_ok=True)

    for person, personData in directConnections.items():

        filePath = os.path.join(peopleDirectory, f"{person}.json")
        personConnections = {}

        if os.path.exists(filePath):
            with open(filePath, "r") as file:
                personConnections = json.load(file)

        url = f'https://www.linkedin.com/search/results/people/?network=["F"]&connectionOf=["{personData["linkedinID"]}"]'

        driver.get(url)
        time.sleep(2 + random.random())

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Each connection is a list item containing a profile link and a message link.
        connectionsDivs = [
            div
            for div in soup.find_all("div", attrs={"role": "listitem"})
            if div.find(
                "a",
                href=lambda href: href and "/in/" in href,
            )
            and div.find(
                "a",
                href=lambda href: href and "recipient=" in href,
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
                (
                    link
                    for link in div.find_all("a", href=True)
                    if "recipient=" in link["href"]
                ),
                None,
            )
            linkedinID = parse_qs(urlparse(messageLink["href"]).query).get(
                "recipient", [None]
            )[0]

            personConnections[profileID] = {
                "name": name,
                "profileUrl": profileUrl,
                "linkedinID": linkedinID,
                "imageUrl": imageUrl,
                "currentJob": currentJob,
            }

        with open(filePath, "w", encoding="utf-8") as file:
            json.dump(personConnections, file, indent=2, ensure_ascii=False)
            file.write("\n")

pass
