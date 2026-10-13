from modules import graph
import networkx as nx
import json
import os

if __name__ == "__main__":
    currentDirectory = os.path.dirname(os.path.abspath(__file__))
    peopleDirectory = os.path.join(currentDirectory, "connections")

    with open(
        os.path.join(currentDirectory, "connections.json"), "r", encoding="utf-8"
    ) as f:
        connections = json.load(f)

    G = nx.MultiDiGraph()

    G.add_nodes_from(
        connections.keys(), type=("Linkedin", "User", "Known"), color="red"
    )

    connectionNames = {}

    for person, personData in connections.items():

        connectionNames[person] = personData["name"]
        filePath = os.path.join(peopleDirectory, f"{person}.json")

        with open(filePath, "r", encoding="utf-8") as f:
            personConnections: dict = json.load(f)

        for p, pData in personConnections.items():
            G.add_edge(person, p)
            connectionNames[p] = pData["name"]

    # Sort the names by value
    connectionNames = dict(
        sorted(connectionNames.items(), key=lambda item: item[1].lower())
    )

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

    html = graph.createHTML(G)

    with open(os.path.join(currentDirectory, "LinkedinGraph.html"), "w") as f:
        f.write(html)
