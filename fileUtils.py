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


def invitationsFilePath() -> str:
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(currentDirectory, "invitations.json")


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


def getInvitations() -> dict[str, str]:
    """
    Get the invitations from the invitations.json file.

    Args:
        - None

    Returns:
        - dict[str, str]: A dictionary containing the invitations.
    """
    invitationsFile = invitationsFilePath()
    return getConnections(invitationsFile)


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


def addNewConnections(personA: str, personB: str, personBName) -> None:
    """
    Add a new connection between two people and save the updated connections.

    Args:
        - personA (str): The identifier of the first person.
        - personB (str): The identifier of the second person.
        - personBName (str): The name of the second person.

    Returns:
        - None
    """
    if not STORE_PROFILES:
        return

    connectionsDirectory = connectionsDirectoryPath()

    inverseConnections = getSecondConnections(personA)
    inverseConnections[personB] = personBName

    inverseFilePath = os.path.join(connectionsDirectory, f"{personA}.json")

    saveConnections(inverseConnections, inverseFilePath)


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


def saveSecondConnections(person: str, name: str, connections: dict[str, str]) -> None:
    """
    Save the connections of a specific person to their corresponding JSON file.

    Args:
        - person (str): The person's identifier in the dictionary of profiles.
        - name (str): The person's name.
        - connections (dict[str, str]): A dictionary containing the connections to save.

    Returns:
        - None
    """
    connectionsDirectory = connectionsDirectoryPath()
    filePath = os.path.join(connectionsDirectory, f"{person}.json")
    saveConnections(connections, filePath)

    # Bidirectional
    for connectionID in connections.keys():

        addNewConnections(connectionID, person, name)


def saveIncompleteConnections(person: str, connections: list[str]) -> None:
    """
    Save some new connections of a specific person to their corresponding JSON file.

    Args:
        - person (str): The person's identifier in the dictionary of profiles.
        - connections (list[str]): A list containing some profiles the person is
            connected to.

    Returns:
        - None
    """
    if not STORE_PROFILES:
        return

    allProfiles = getProfiles()

    # Try to get the names
    name = allProfiles.get(person, {}).get("name", "Unknown")
    connectionsWithNames = {
        connection: allProfiles.get(connection, {}).get("name", "Unknown")
        for connection in connections
    }

    for connectionID, connectionName in connectionsWithNames.items():
        addNewConnections(connectionID, person, name)
        addNewConnections(person, connectionID, connectionName)


def saveInvitations(connections: dict[str, str]) -> None:
    """
    Save the invitations to the invitations.json file.

    Args:
        - connections (dict[str, str]): A dictionary containing the invitations to save.

    Returns:
        - None
    """
    saveConnections(connections, invitationsFilePath())


def addMissingProfiles() -> None:
    """
    If profiles.jso is corrupted or missing, this function will
    try to add the missing profiles from the connections and invitations.

    Because the other files only store the url and name, only those fields
    will be added to the profiles.json file.

    Args:
        - None

    Returns:
        - None
    """
    allProfiles = getProfiles()

    # Dict where all the connections and invitations will be stored
    connectionProfiles: dict[str, str] = {}

    # Start by adding the second-degree connections
    peopleDirectory = connectionsDirectoryPath()
    connectionFiles = [f for f in os.listdir(peopleDirectory) if f.endswith(".json")]

    for person in connectionFiles:

        filePath = os.path.join(peopleDirectory, person)

        with open(filePath, "r", encoding="utf-8") as f:
            personConnections: dict = json.load(f)

        connectionProfiles.update(personConnections)

    # Add the invitations
    invitations = getInvitations()
    connectionProfiles.update(invitations)

    # Add the first-degree connections
    firstConnections = getFirstConnections()
    connectionProfiles.update(firstConnections)

    for person, name in connectionProfiles.items():
        if person not in allProfiles:
            personData = {
                "name": name,
                "profileUrl": f"https://www.linkedin.com/in/{person}/",
                "imageUrls": [],
            }

            if person in firstConnections:
                personData["degree"] = 1
            elif person not in invitations:
                """
                The only other way to have a connection is to be connected
                to a first-degree connection, which makes it a second-degree connection.

                Linkedin doesn't allow to see connections between users that are not
                connected to you.
                """
                personData["degree"] = 2

            allProfiles[person] = personData

    # Finally, save the profiles.json file
    saveProfiles(allProfiles)
