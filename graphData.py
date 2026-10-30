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

            previousRounded = round(values[i - 1], decimals) if i > 0 else None
            previousTrunc = (
                int(values[i - 1] * (10**decimals)) / (10**decimals) if i > 0 else None
            )

            nextRounded = (
                round(values[i + 1], decimals) if i < len(values) - 1 else None
            )
            nextTrunc = (
                int(values[i + 1] * (10**decimals)) / (10**decimals)
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
        image = (
            f'<a href="{profile["profileUrl"]}" target="_blank" rel="noopener noreferrer">'
            + f'<img src="{profile["imageUrl"]}" width="100" height="100"></a>'
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

        filePath = os.path.join(peopleDirectory, f"{person}.json")

        with open(filePath, "r", encoding="utf-8") as f:
            personConnections: dict = json.load(f)

        for p, pData in personConnections.items():
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

    # Calculate the connection score for each profile

    # Score for Unkown nodes is the number of connections they have with Known nodes
    for n, d in G.nodes(data=True):

        if "Unknown" in d["type"]:
            connectedNodes = set(G.successors(n)) | set(G.predecessors(n))
            d["score"] = len(connectedNodes)

    # Score for Known nodes is the sum of the scores of the Unknown nodes they are connected to
    # inversely weighted by the score of the Unknown node
    for n, d in G.nodes(data=True):

        if "Known" in d["type"]:
            connectedNodes = set(G.successors(n)) | set(G.predecessors(n))

            scoreFromUnknown = 0

            for connectedNode in connectedNodes:

                if "Unknown" in G.nodes[connectedNode]["type"]:
                    scoreFromUnknown += 1 / G.nodes[connectedNode]["score"]

            d["score"] = scoreFromUnknown

    # Obtain the scores
    nodesWithScores = {}
    for n, d in G.nodes(data=True):
        if "Known" in d["type"] or d["score"] > 0:
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
