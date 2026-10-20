from bs4 import BeautifulSoup
import fileUtils

fileUtils.STORE_PROFILES = False  # Disable storing profiles during tests

import linkedinHtml
import unittest
import json
import os


def create_test_method(file_path: str) -> callable:
    """
    Creates a test method and sets its name.

    Args:
        - file_path (str): The path to the file to be tested.

    Returns:
        - callable: The created test method.
    """

    def test_method(self: unittest.TestCase) -> None:
        """
        Open the file at the given path, parse it with BeautifulSoup, and extract LinkedIn connections.

        Args:
            - self (unittest.TestCase): The instance of the test case.

        Returns:
            - None
        """
        with open(file_path, "r", encoding="utf-8") as file:
            soup = BeautifulSoup(file, "html.parser")

        # Get the json file path corresponding to the html file
        jsonFilePath = file_path.replace(".html", ".json")

        with open(jsonFilePath, "r", encoding="utf-8") as jsonFile:
            expectedData = json.load(jsonFile)

        obtainedData = linkedinHtml.extractProfiles([soup])

        self.maxDiff = None  # Show full diff in case of assertion failure
        self.assertEqual(obtainedData, expectedData)

    test_method.__name__ = f"test_{os.path.basename(file_path)}"
    return test_method


def addTests(cls: type, path: str) -> None:
    """
    Dynamically adds test methods to the given class based on the files in the specified path.

    Args:
        - cls (type): The class to which the test methods will be added.
        - path (str): The directory path containing the files to create test methods for.

    Returns:
        - None
    """
    for fileName in sorted(os.listdir(path)):

        if fileName.endswith(".html"):

            filePath = os.path.join(path, fileName)

            if os.path.isfile(filePath):
                test_method = create_test_method(filePath)
                setattr(cls, test_method.__name__, test_method)


currentDirectory = os.path.dirname(os.path.abspath(__file__))
extractProfilesPath = os.path.join(currentDirectory, "extractProfiles")
DynamicTestClass = type("extractProfiles", (unittest.TestCase,), {})

addTests(DynamicTestClass, extractProfilesPath)
globals()["extractProfiles"] = DynamicTestClass

if "DynamicTestClass" in globals():
    del globals()["DynamicTestClass"]
