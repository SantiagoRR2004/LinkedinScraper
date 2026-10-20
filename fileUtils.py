import unicodedata
import random
import json
import time
import os

STORE_PROFILES = True


def waitRandomTime(randomSeconds: float = 60) -> None:
    """
    Wait for a random amount of time between 2 and 2 + randomSeconds seconds.

    Args:
        - randomSeconds (float): The maximum number of seconds to wait. Default is 60.

    Returns:
        - None
    """
    timeToWait = 2 + randomSeconds * random.random()
    time.sleep(timeToWait)


def normalizeName(name: str) -> str:
    """
    Normalize the name by removing accents and converting it to lowercase.

    Args:
        - name (str): The name to normalize.

    Returns:
        - str: The normalized name.
    """
    return (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    )


def profileFilePath() -> str:
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(currentDirectory, "profiles.json")


def firstConnectionsFilePath() -> str:
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(currentDirectory, "connections.json")


def connectionsDirectoryPath() -> str:
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    connectionsDirectory = os.path.join(currentDirectory, "connections")
    os.makedirs(connectionsDirectory, exist_ok=True)
    return connectionsDirectory


def getProfiles() -> dict[str, dict]:
    """
    Get the profiles from the profiles.json file.

    Args:
        - None

    Returns:
        - dict[str, dict]: A dictionary containing the profiles.
    """
    completeProfilesFile = profileFilePath()

    profiles = {}
    if os.path.exists(completeProfilesFile) and STORE_PROFILES:
        with open(completeProfilesFile, "r", encoding="utf-8") as f:
            profiles = json.load(f)

    return profiles


def getConnections(filePath: str) -> dict[str, str]:
    """
    Get the connections from the specified JSON file.

    Args:
        - filePath (str): The path to the JSON file containing the connections.

    Returns:
        - dict[str, str]: A dictionary containing the connections.
    """
    connections = {}
    if os.path.exists(filePath) and STORE_PROFILES:
        with open(filePath, "r", encoding="utf-8") as f:
            connections = json.load(f)

    return connections


def getFirstConnections() -> dict[str, str]:
    """
    Get the first connections from the connections.json file.

    Args:
        - None

    Returns:
        - dict[str, str]: A dictionary containing the first connections.
    """
    firstConnectionsFile = firstConnectionsFilePath()
    return getConnections(firstConnectionsFile)


def getSecondConnections(person: str) -> dict[str, str]:
    """
    Get the connections of a specific person from their corresponding JSON file.

    Args:
        - person (str): The person's identifier in the dictionary of profiles.

    Returns:
        - dict[str, str]: A dictionary containing the connections of the specified person.
    """
    connectionsDirectory = connectionsDirectoryPath()
    filePath = os.path.join(connectionsDirectory, f"{person}.json")
    return getConnections(filePath)


def saveProfiles(profiles: dict[str, dict]) -> None:
    """
    Save the profiles to the profiles.json file.

    Args:
        - profiles (dict[str, dict]): A dictionary containing the profiles to save.

    Returns:
        - None
    """
    profiles = dict(sorted(profiles.items(), key=lambda x: normalizeName(x[1]["name"])))

    if not STORE_PROFILES:
        return

    completeProfilesFile = profileFilePath()

    # Sort by name
    with open(completeProfilesFile, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
        f.write("\n")


def saveConnections(connections: dict[str, str], filePath: str) -> None:
    """
    Save the connections to the specified JSON file.

    Args:
        - connections (dict[str, str]): A dictionary containing the connections to save.
        - filePath (str): The path to the JSON file where the connections will be saved.

    Returns:
        - None
    """
    # Sort by name
    connections = dict(sorted(connections.items(), key=lambda x: normalizeName(x[1])))

    if not STORE_PROFILES:
        return

    with open(filePath, "w", encoding="utf-8") as f:
        json.dump(connections, f, ensure_ascii=False, indent=2)
        f.write("\n")


def saveFirstConnections(firstConnections: dict[str, str]) -> None:
    """
    Save the first connections to the connections.json file.

    Args:
        - firstConnections (dict[str, str]): A dictionary containing the first connections to save.

    Returns:
        - None
    """
    firstConnectionsFile = firstConnectionsFilePath()
    saveConnections(firstConnections, firstConnectionsFile)


def saveSecondConnections(person: str, connections: dict[str, str]) -> None:
    """
    Save the connections of a specific person to their corresponding JSON file.

    Args:
        - person (str): The person's identifier in the dictionary of profiles.
        - connections (dict[str, str]): A dictionary containing the connections to save.

    Returns:
        - None
    """
    connectionsDirectory = connectionsDirectoryPath()
    filePath = os.path.join(connectionsDirectory, f"{person}.json")
    saveConnections(connections, filePath)
