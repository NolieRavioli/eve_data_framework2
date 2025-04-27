# util/sde.py

import os
import yaml
import logging
from db.database import get_public_session
from db.models import SolarSystem, Stargate

logger = logging.getLogger(__name__)

# ──────── Globals ─────────────────────────────────────────────────────────────
BASE_SDE_PATH = os.getenv("SDE_PATH", "_sde")
TYPES_YAML_PATH = os.path.join(BASE_SDE_PATH, "fsd", "types.yaml")
UNIVERSE_PATH = os.path.join(BASE_SDE_PATH, "fsd", "universe")

_type_id_to_name = None

# ──────── Loader ──────────────────────────────────────────────────────────────

def load_sde_data():
    """Load the types.yaml file into memory."""
    global _type_id_to_name
    if _type_id_to_name is not None:
        return  # Already loaded

    if not os.path.exists(TYPES_YAML_PATH):
        logger.error(f"types.yaml not found at {TYPES_YAML_PATH}")
        _type_id_to_name = {}
        return

    with open(TYPES_YAML_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if isinstance(data, dict):
        _type_id_to_name = {
            int(type_id): props.get("name", {}).get("en", f"Unknown {type_id}")
            for type_id, props in data.items()
        }
        logger.info(f"Loaded {len(_type_id_to_name)} type names from types.yaml")
    else:
        logger.error("Unexpected types.yaml structure!")
        _type_id_to_name = {}

# ──────── Public API ──────────────────────────────────────────────────────────

def name_from_id(type_id: int) -> str:
    """Given a typeID, return the item name from SDE, or 'Unknown'."""
    if _type_id_to_name is None:
        load_sde_data()

    return _type_id_to_name.get(type_id, f"Unknown TypeID {type_id}")

def build_universe_table():
    """Builds database tables from static data export for fast reference."""
    session = get_public_session()
    logger.info("Starting build_tables()")

    # Map for quickly resolving stargate relationships
    stargate_map = {}

    for root, dirs, files in os.walk(UNIVERSE_PATH):
        for file in files:
            if file == "solarsystem.staticdata.yaml":
                system_path = os.path.join(root, file)
                with open(system_path, "r", encoding="utf-8") as f:
                    system_data = yaml.safe_load(f)

                system_id = int(system_data["solarSystemID"])
                system_name = system_data.get("solarSystemName", f"Unknown {system_id}")
                constellation_id = system_data.get("constellationID")
                region_id = system_data.get("regionID")
                planets = len(system_data.get("planets", []))
                moons = sum(len(p.get("moons", [])) for p in system_data.get("planets", []))
                stargates = system_data.get("stargates", {})
                security = system_data.get("security", 0.0)
                solar_system_name_id = system_data.get("solarSystemNameID")

                # Insert system
                session.merge(System(
                    system_id=system_id,
                    system_name=system_name,
                    constellation_id=constellation_id,
                    region_id=region_id,
                    planets=planets,
                    moons=moons,
                    stargates=len(stargates),
                    security=security,
                    solar_system_name_id=solar_system_name_id,
                ))

                # Insert stargates
                for gate_id_str, gate_data in stargates.items():
                    gate_id = int(gate_id_str)
                    dest_gate_id = int(gate_data.get("destination"))
                    pos = gate_data.get("position", [0.0, 0.0, 0.0])
                    type_id = gate_data.get("typeID")

                    stargate_obj = Stargate(
                        gate_id=gate_id,
                        system_id=system_id,
                        destination_gate_id=dest_gate_id,
                        destination_system_id=None,  # Will update if destination already known
                        position_x=pos[0],
                        position_y=pos[1],
                        position_z=pos[2],
                        type_id=type_id,
                    )

                    session.merge(stargate_obj)
                    stargate_map[gate_id] = (system_id, dest_gate_id)

                    # Try to resolve destination_system_id immediately
                    if dest_gate_id in stargate_map:
                        dest_system_id, _ = stargate_map[dest_gate_id]

                        # Update both sides
                        existing_gate = session.query(Stargate).get(dest_gate_id)
                        if existing_gate:
                            existing_gate.destination_system_id = system_id
                            session.merge(existing_gate)

                        stargate_obj.destination_system_id = dest_system_id
                        session.merge(stargate_obj)

    session.commit()
    session.close()
    logger.info("build_tables() complete!")
