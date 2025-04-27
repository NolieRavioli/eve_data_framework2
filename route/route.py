# route/route.py

import os
import logging
import requests
from util.utils import resolve_names_to_ids

ESI = "https://esi.evetech.net/latest"
HEADERS = {"Accept": "application/json"}

MODULE_DIR  = os.path.dirname(os.path.abspath(__file__))
JUMPGATE_PATH = os.path.join(MODULE_DIR, ".gitignore", "JUMPGATES.txt")

def getRoute(origin, destination):
    jump_pairs = []
    all_keys = set()

    with open(JUMPGATE_PATH, 'r') as f:
        for line in f:
            a, b = line.strip().split(',')
            jump_pairs.append((a, b))
            all_keys.update([a, b])

    all_keys.update([str(origin), str(destination)])

    # Identify string-based names (non-numeric)
    names_to_resolve = [k for k in all_keys if not k.isdigit()]
    name_to_id = resolve_names_to_ids(names_to_resolve)

    def to_id(val):
        return int(val) if str(val).isdigit() else name_to_id.get(val)

    # Validate input
    origin_id = to_id(origin)
    destination_id = to_id(destination)

    if origin_id is None or destination_id is None:
        logging.error("Origin or destination name could not be resolved.")
        return

    connections = ",".join(
        f"{to_id(a)}|{to_id(b)}"
        for a, b in jump_pairs
        if to_id(a) is not None and to_id(b) is not None
    )

    route_url = (
        f"{ESI}/route/{origin_id}/{destination_id}/"
        f"?connections={connections}&datasource=tranquility&flag=shortest"
    )

    resp = requests.get(route_url, headers=HEADERS)
    print(f"ROUTE RESPONSE {resp.status_code}: {resp.text}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    getRoute(30000142, 30005133)
