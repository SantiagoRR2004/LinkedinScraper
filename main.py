from bs4 import BeautifulSoup
import firstConnections
import linkedinHtml
import driverUtils
import random
import time
import os

if __name__ == "__main__":
    driver = driverUtils.createDriver()
    directConnections = firstConnections.obtainDirectConnections(driver)

    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    peopleDirectory = os.path.join(currentDirectory, "connections")
    os.makedirs(peopleDirectory, exist_ok=True)

    for person, personData in directConnections.items():

        filePath = os.path.join(peopleDirectory, f"{person}.json")

        for n in ["F", "S"]:

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
                time.sleep(2 + 2 * random.random())

                soup = BeautifulSoup(driver.page_source, "html.parser")

                connections = linkedinHtml.extractLinkedinConnections(soup, filePath)

                nConnections = len(connections)
                page += 1
                time.sleep(2 + 2 * random.random())

pass
