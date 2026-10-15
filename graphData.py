from modules import graph
import networkx as nx
import unicodedata
import json
import os


def normalizeName(name: str) -> str:
    return (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    )


if __name__ == "__main__":
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    peopleDirectory = os.path.join(currentDirectory, "connections")

    with open(
        os.path.join(currentDirectory, "profiles.json"), "r", encoding="utf-8"
    ) as f:
        profiles = json.load(f)
    with open(
        os.path.join(currentDirectory, "connections.json"), "r", encoding="utf-8"
    ) as f:
        firstConnections = json.load(f)

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

    # Obtain the Unknown nodes with their number of connections
    unknownNodes = {
        n: G.degree(n)
        for n, d in G.nodes(data=True)
        if "Unknown" in d["type"] and G.degree(n) > 1
    }
    unknownNodes = dict(
        sorted(
            unknownNodes.items(),
            key=lambda x: (-x[1], normalizeName(profiles[x[0]]["name"])),
            reverse=False,
        )
    )

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

    assert len(connectionNames.keys()) == len(set(connectionNames.values()))
    nx.relabel_nodes(G, connectionNames, copy=False)

    with open(os.path.join(currentDirectory, "LinkedinGraphComplete.html"), "w") as f:
        f.write(graph.createHTML(G))

    G = graph.removeUnconnectedNodes(G, "Known")

    with open(os.path.join(currentDirectory, "LinkedinGraph.html"), "w") as f:
        f.write(graph.createHTML(G))

    # Generate HTML
    html = (
        '<div style="text-align: center;">'
        "<h1>Profiles</h1>"
        '<table style="margin: 0 auto; border-spacing: 12px 0;">'
        "<thead><tr>"
        '<th style=""></th>'
        '<th style=""></th>'
        '<th style=""></th>'
        "</tr></thead><tbody>"
    )
    for node, degree in unknownNodes.items():
        profile = profiles[node]
        image = (
            f'<img src="{profile["imageUrl"]}" alt="{profile["name"]}" '
            'width="100" height="100"> '
        )
        html += (
            "<tr>"
            f'<td style="padding: 0; text-align: right">{degree}</td>'
            f'<td style="padding: 0;">{image}</td>'
            f'<td style="padding: 0; text-align: left">{profile["name"]}<br>{profile["currentJob"]}</td>'
            "</tr>"
        )
    html += "</tbody></table></div>"

    with open(os.path.join(currentDirectory, "profiles.html"), "w") as f:
        f.write(html)
