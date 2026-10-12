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

        url = (
            "https://www.linkedin.com/search/results/people/?"
            + 'network=["F"]'
            + "&"
            + f'connectionOf=["{personData["linkedinID"]}"]'
        )

        driver.get(url)
        time.sleep(2 + random.random())

        soup = BeautifulSoup(driver.page_source, "html.parser")

        linkedinHtml.extractLinkedinConnections(soup, filePath)

pass
