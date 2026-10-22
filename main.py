import linkedinScraper
import driverUtils

if __name__ == "__main__":
    driver = driverUtils.createDriver()
    linkedinScraper.obtainDirectConnections(driver)
    linkedinScraper.obtainInterpersonalConnections(driver)
    driver.quit()

pass
