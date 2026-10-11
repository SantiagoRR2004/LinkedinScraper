import firstConnections
import driverUtils

if __name__ == "__main__":
    driver = driverUtils.createDriver()
    directConnections = firstConnections.obtainDirectConnections(driver)
pass
