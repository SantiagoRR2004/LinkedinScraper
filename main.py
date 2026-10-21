from bs4 import BeautifulSoup
import firstConnections
import linkedinHtml
import driverUtils
import fileUtils

if __name__ == "__main__":
    driver = driverUtils.createDriver()
    directConnections = firstConnections.obtainDirectConnections(driver)

    allProfiles = fileUtils.getProfiles()

    reverseImage = {v["imageUrl"]: k for k, v in allProfiles.items()}

    for person, personData in allProfiles.items():

        if personData.get("linkedinID") is None:
            continue

        previousConnections = fileUtils.getSecondConnections(person)

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

pass
