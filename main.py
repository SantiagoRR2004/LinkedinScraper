import linkedinScraper
import driverUtils

if __name__ == "__main__":
    driver = driverUtils.createDriver()
    linkedinScraper.obtainDirectConnections(driver)
    linkedinScraper.obtainGrowingNetwork(driver)
    linkedinScraper.obtainInvitations(driver)
    linkedinScraper.scrapeMainProfiles(driver)
    linkedinScraper.obtainInterpersonalConnections(driver)
