from modules import graph
import networkx as nx
import fileUtils
import json
import os


def adaptiveRounding(values: list[float], maxDecimals: int = 10) -> list[float]:
    """
    Rounds the values in the list to a number of decimals that ensures that no two consecutive
    values are equal after rounding.

    It also checks truncation to avoid cases like 10.5 and 10.4 being
    rounded to 11 and 10 respectively.

    Args:
        - values (list[float]): The list of values to be rounded.
        - maxDecimals (int): The maximum number of decimals to round to.

    Returns:
        - list[float]: The list of rounded values.
    """
    result = []

    for i, value in enumerate(values):
        for decimals in range(0, maxDecimals + 1):
            rounded = round(value, decimals)
            trunc = int(rounded * (10**decimals)) / (10**decimals)

            # Find the previous value that is different
            j = i - 1
            while j > 0 and values[j] == value:
                j -= 1

            previousRounded = round(values[j], decimals) if i > 0 else None
            previousTrunc = (
                int(values[j] * (10**decimals)) / (10**decimals) if i > 0 else None
            )

            # Find the next value that is different
            j = i + 1
            while j < len(values) - 1 and values[j] == value:
                j += 1

            nextRounded = round(values[j], decimals) if i < len(values) - 1 else None
            nextTrunc = (
                int(values[j] * (10**decimals)) / (10**decimals)
                if i < len(values) - 1
                else None
            )

            roundedOk = rounded not in (
                previousRounded,
                previousTrunc,
                nextRounded,
                nextTrunc,
            )
            truncOk = trunc not in (
                previousRounded,
                previousTrunc,
                nextRounded,
                nextTrunc,
            )

            if roundedOk and truncOk:
                break

        result.append(rounded)

    return result


def createHTMLList(nodes: dict[str, float], title: str, useColor: bool = False) -> str:
    """
    Creates an HTML list of profiles with their scores.

    Args:
        - nodes (dict[str, float]): A dictionary of nodes with their scores.
        - title (str): The title for the HTML list.
        - useColor (bool): Whether to color the scores based on their type (Known or Unknown).

    Returns:
        - str: An HTML string representing the list of profiles with their scores.
    """
    nodes = dict(
        sorted(
            nodes.items(),
            key=lambda x: (-x[1], fileUtils.normalizeName(profiles[x[0]]["name"])),
            reverse=False,
        )
    )

    # Replace the scores with the rounded scores
    nodes = dict(
        zip(
            nodes.keys(),
            adaptiveRounding(list(nodes.values())),
        )
    )

    html = (
        '<div style="text-align: center;">'
        f"<h1>{title}</h1>"
        '<table style="margin: 0 auto; border-spacing: 12px 0;">'
        "<thead><tr>"
        '<th style=""></th>'
        '<th style=""></th>'
        '<th style=""></th>'
        "</tr></thead><tbody>"
    )

    color = ""

    for node, score in nodes.items():
        profile = profiles[node]
        imageUrls = profile.get("imageUrls")
        image = (
            f'<a href="{profile["profileUrl"]}" target="_blank" rel="noopener noreferrer">'
            + f'<img src="{imageUrls[0] if imageUrls else ""}" width="100" height="100"></a>'
        )

        if useColor:
            color = "color: " + ("red" if node in firstConnections else "blue") + ";"

        html += (
            "<tr>"
            f'<td style="padding: 0; text-align: right; {color}">{format(score, '.15g')}</td>'
            f'<td style="padding: 0;">{image}</td>'
            f'<td style="padding: 0; text-align: left">{profile["name"]}<br>{profile["currentJob"]}'
        )

        if profile.get("location"):
            html += f'<br>{profile["location"]}'

        html += "</td></tr>"

    html += "</tbody></table></div>"

    return html


if __name__ == "__main__":
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    peopleDirectory = os.path.join(currentDirectory, "connections")

    profiles = fileUtils.getProfiles()
    firstConnections = fileUtils.getFirstConnections()

    G = nx.MultiDiGraph()

    G.add_nodes_from(firstConnections.keys(), type=("Linkedin", "Known"), color="red")
    for person, personData in profiles.items():
        if person not in firstConnections:
            G.add_node(person, type=("Linkedin", "Unknown"), color="blue")

    # Load the connection files
    connectionFiles = [
        f[: -len(".json")] for f in os.listdir(peopleDirectory) if f.endswith(".json")
    ]

    for person in connectionFiles:

        if person not in G.nodes():
            print(f"{person} not in profiles.json")
            continue

        filePath = os.path.join(peopleDirectory, f"{person}.json")

        with open(filePath, "r", encoding="utf-8") as f:
            personConnections: dict = json.load(f)

        for p, pData in personConnections.items():

            if p not in G.nodes():
                print(f"{p} not in profiles.json")
                continue

            G.add_edge(person, p)

    # Remove the nodes that are not connected to any Known nodes
    G.remove_nodes_from(
        [
            node
            for node in G.nodes()
            if "Known" not in G.nodes[node]["type"]
            and len(set(G.successors(node)) | set(G.predecessors(node))) == 0
        ]
    )

    # Calculate number of connections as intermediate result
    for n, d in G.nodes(data=True):
        connectedNodes = set(G.successors(n)) | set(G.predecessors(n))
        d["numConnections"] = len(connectedNodes)

    maxneighbourhoodExclusivityKnown = 0
    maxneighbourhoodExclusivityUnknown = 0
    maxknownConnectionsPercentage = 0
    maxknownConnectionsOfTotalPercentage = 0

    # Calculate the connection score for each profile
    for n, d in G.nodes(data=True):

        connectedNodes = set(G.successors(n)) | set(G.predecessors(n))

        scoreFromOthers = 0
        numKnownConnections = 0

        for connectedNode in connectedNodes:

            scoreFromOthers += 1 / G.nodes[connectedNode]["numConnections"]

            if "Known" in G.nodes[connectedNode]["type"]:
                numKnownConnections += 1

        d["neighbourhoodExclusivity"] = (
            100 * scoreFromOthers / d["numConnections"]
            if d["numConnections"] > 0
            else 0
        )
        if "Known" in d["type"]:
            maxneighbourhoodExclusivityKnown = max(
                maxneighbourhoodExclusivityKnown, d["neighbourhoodExclusivity"]
            )
        else:
            maxneighbourhoodExclusivityUnknown = max(
                maxneighbourhoodExclusivityUnknown, d["neighbourhoodExclusivity"]
            )

        d["knownConnectionsPercentage"] = (
            100 * numKnownConnections / len(firstConnections)
        )
        maxknownConnectionsPercentage = max(
            maxknownConnectionsPercentage, d["knownConnectionsPercentage"]
        )

        if profiles[n].get("nContacts") is not None:
            numConnections = profiles[n]["nContacts"]
            d["knownConnectionsOfTotalPercentage"] = (
                100 * numKnownConnections / (numConnections + numKnownConnections)
                if numConnections > 0
                else 0
            )
        else:
            d["knownConnectionsOfTotalPercentage"] = 0

        maxknownConnectionsOfTotalPercentage = max(
            maxknownConnectionsOfTotalPercentage, d["knownConnectionsOfTotalPercentage"]
        )

    # Use the mean of the normalized values
    for n, d in G.nodes(data=True):

        scoreParts = []

        if "Known" in d["type"]:
            scoreParts.append(
                100 * d["neighbourhoodExclusivity"] / maxneighbourhoodExclusivityKnown
            )
        else:
            scoreParts.append(
                100 * d["neighbourhoodExclusivity"] / maxneighbourhoodExclusivityUnknown
            )

        scoreParts.append(
            100 * d["knownConnectionsPercentage"] / maxknownConnectionsPercentage
        )
        scoreParts.append(
            100
            * d["knownConnectionsOfTotalPercentage"]
            / maxknownConnectionsOfTotalPercentage
        )

        d["score"] = sum(scoreParts) / len(scoreParts)

    # Obtain the scores
    nodesWithScores = {}
    for n, d in G.nodes(data=True):
        nodesWithScores[n] = d["score"]

    # Rename the nodes
    connectionNames = {k: v["name"] for k, v in profiles.items()}

    if len(connectionNames.keys()) != len(set(connectionNames.values())):
        duplicates = set(
            name
            for name in connectionNames.values()
            if list(connectionNames.values()).count(name) > 1
        )
        for duplicate in duplicates:
            print(duplicate)

            # Fix by adding a number to the duplicate names
            count = 1

            for k, v in connectionNames.items():
                if v == duplicate:
                    connectionNames[k] = f"{v} ({count})"
                    count += 1

    assert len(connectionNames.keys()) == len(set(connectionNames.values()))
    nx.relabel_nodes(G, connectionNames, copy=False)

    with open(os.path.join(currentDirectory, "LinkedinGraphComplete.html"), "w") as f:
        f.write(graph.createHTML(G))

    G = graph.removeUnconnectedNodes(G, "Known")

    with open(os.path.join(currentDirectory, "LinkedinGraph.html"), "w") as f:
        f.write(graph.createHTML(G))

    # Known profiles
    html = createHTMLList(
        {k: v for k, v in nodesWithScores.items() if k in firstConnections},
        "Connections",
    )
    with open(os.path.join(currentDirectory, "profilesKnown.html"), "w") as f:
        f.write(html)

    # Profiles that are not my connections
    html = createHTMLList(
        {k: v for k, v in nodesWithScores.items() if k not in firstConnections},
        "Profiles that are not my connections",
    )
    with open(os.path.join(currentDirectory, "profilesUnknown.html"), "w") as f:
        f.write(html)

    # Profiles in general
    html = createHTMLList(
        {k: v for k, v in nodesWithScores.items() if k in firstConnections or v > 1},
        "Profiles",
        useColor=True,
    )
    with open(os.path.join(currentDirectory, "profiles.html"), "w") as f:
        f.write(html)
