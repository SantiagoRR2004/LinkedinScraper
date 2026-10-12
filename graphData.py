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

    for person in connections.keys():
        filePath = os.path.join(peopleDirectory, f"{person}.json")
        with open(filePath, "r", encoding="utf-8") as f:
            data: dict = json.load(f)

        for p in data.keys():
            G.add_edge(person, p)

    html = graph.createHTML(G)

    with open(os.path.join(currentDirectory, "LinkedinGraph.html"), "w") as f:
        f.write(html)
