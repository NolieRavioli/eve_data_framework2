import os
import json
import yaml
import heapq
from collections import deque

# Paths
MODULE_DIR  = os.path.dirname(os.path.abspath(__file__))
SYSTEM_GRAPH_FILE = os.path.join(MODULE_DIR, ".gitignore", "system_graph.json")

SDE_UNIVERSE_FOLDER = "../_sde/universe/eve"
# Use faster CLoader if available
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import SafeLoader as Loader


def load_stargate_map():
    """Builds a mapping from stargate ID to its parent solar system ID."""
    stargate_to_system = {}
    for root, _, files in os.walk(SDE_UNIVERSE_FOLDER):
        for file in files:
            if file == "solarsystem.yaml":
                with open(os.path.join(root, file), encoding="utf-8") as f:
                    data = yaml.load(f, Loader=Loader)
                sys_id = data.get("solarSystemID")
                for gate_id in data.get("stargates", {}):
                    stargate_to_system[int(gate_id)] = sys_id
    return stargate_to_system


def build_graph():
    """Crawls the SDE_UNIVERSE_FOLDER and builds an adjacency map of solar systems."""
    gate_map = load_stargate_map()
    graph = {}

    for root, _, files in os.walk(SDE_UNIVERSE_FOLDER):
        for file in files:
            if file == "solarsystem.yaml":
                with open(os.path.join(root, file), encoding="utf-8") as f:
                    data = yaml.load(f, Loader=Loader)
                src_sys = data.get("solarSystemID")
                graph.setdefault(src_sys, [])
                for info in data.get("stargates", {}).values():
                    dest_gate = info.get("destination")
                    dest_sys  = gate_map.get(dest_gate)
                    if dest_sys is not None:
                        graph[src_sys].append(dest_sys)

    # ensure bidirectional
    for src, neighbors in list(graph.items()):
        for dest in neighbors:
            graph.setdefault(dest, [])
            if src not in graph[dest]:
                graph[dest].append(src)

    return graph


def save_graph(graph, path=SYSTEM_GRAPH_FILE):
    """Saves the system graph to JSON on disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(graph, f)


def load_graph(path=SYSTEM_GRAPH_FILE):
    """Loads the system graph from JSON on disk."""
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def dijkstra(start_sys, end_sys, graph):
    """Returns the minimum number of jumps between start_sys and end_sys."""
    # Unweighted: BFS
    visited = {start_sys}
    queue = deque([(start_sys, 0)])
    while queue:
        sys_id, dist = queue.popleft()
        if sys_id == end_sys:
            return dist
        for nbr in graph.get(sys_id, []):
            if nbr not in visited:
                visited.add(nbr)
                queue.append((nbr, dist + 1))
    # no route
    return None


if __name__ == "__main__":
    # Build and save if missing
    if not os.path.exists(SYSTEM_GRAPH_FILE):
        print("Building system graph...")
        g = build_graph()
        save_graph(g)
        print(f"Graph saved to {SYSTEM_GRAPH_FILE} ({len(g)} systems) ")
    # Example usage
    graph = load_graph()
    start, end = list(graph.keys())[:2]
    print(f"Jumps from {start} to {end}: {dijkstra(start, end, graph)}")
