from modules import graph
import networkx as nx
import json
import os

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
            G.add_node(person, type=("Linkedin", "Unknown"))

    for person in firstConnections.keys():

        filePath = os.path.join(peopleDirectory, f"{person}.json")

        with open(filePath, "r", encoding="utf-8") as f:
            personConnections: dict = json.load(f)

        for p, pData in personConnections.items():
            G.add_edge(person, p)

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
