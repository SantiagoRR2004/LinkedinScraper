from bs4 import BeautifulSoup
import firstConnections
import linkedinHtml
import driverUtils
import random
import json
import time
import os

if __name__ == "__main__":
    driver = driverUtils.createDriver()
    directConnections = firstConnections.obtainDirectConnections(driver)

    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    peopleDirectory = os.path.join(currentDirectory, "connections")
    os.makedirs(peopleDirectory, exist_ok=True)

    with open(os.path.join(currentDirectory, "profiles.json"), "r") as f:
        allProfiles = json.load(f)

    reverseImage = {v["imageUrl"]: k for k, v in allProfiles.items()}

    for person, personData in allProfiles.items():

        if personData.get("linkedinID") is None:
            continue

        filePath = os.path.join(peopleDirectory, f"{person}.json")

        previousConnections = {}
        if os.path.exists(filePath):
            with open(filePath, "r") as f:
                previousConnections = json.load(f)

        typesOfConnections = []

        if personData.get("hasCommonContacts") and not any(
            p for p in previousConnections if p in directConnections
        ):
            typesOfConnections.append("F")

        if (
            personData.get("nContacts", 0) > len(previousConnections)
            and person in directConnections
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
                time.sleep(2 + 60 * random.random())

                soup = BeautifulSoup(driver.page_source, "html.parser")

                foundConnections = linkedinHtml.extractLinkedinConnections(
                    soup, filePath
                )

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
                        with open(filePath, "r", encoding="utf-8") as f:
                            previousConnections = json.load(f)

                        previousConnections.update(
                            {k: v["name"] for k, v in extraConnections.items()}
                        )
                        previousConnections = dict(
                            sorted(
                                previousConnections.items(), key=lambda x: x[1].lower()
                            )
                        )

                        with open(filePath, "w", encoding="utf-8") as f:
                            json.dump(
                                previousConnections, f, ensure_ascii=False, indent=2
                            )
                            f.write("\n")

                nConnections = len(foundConnections)
                page += 1
                time.sleep(2 + 60 * random.random())

pass
