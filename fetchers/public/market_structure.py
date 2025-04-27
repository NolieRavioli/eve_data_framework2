# fetchers/public/market_structure.py

import os
import yaml
import logging
import requests
from datetime import datetime
from typing import Optional

from db.database import get_public_session
from db.models import Structure, MarketStructure, MarketOrder, Asset, IndustryJob
from util.utils import get_token

logger = logging.getLogger(__name__)

# ──────── Globals ─────────────────────────────────────────────────────────────
ESI_BASE = "https://esi.evetech.net/latest"
DATASOURCE = {"datasource": "tranquility"}
CONFIG_PATH = os.getenv("CONFIG_FILE", "config.yaml")
INT32_MAX = 2_147_483_647

# ──────── Helper Functions ─────────────────────────────────────────────────────

def fetch_public_structures() -> set[int]:
    """Fetch all public Upwell structures."""
    url = f"{ESI_BASE}/universe/structures/"
    resp = requests.get(url, params=DATASOURCE)
    resp.raise_for_status()
    return set(resp.json())

def discover_private_structure_ids(owner_id: int) -> set[int]:
    """Discover potential private structure IDs from private assets and industry jobs."""
    ids = set()
    with get_db_session(owner_id=owner_id) as session:
        for (loc,) in session.query(Asset.location_id).distinct():
            if loc and loc > INT32_MAX:
                ids.add(loc)
        for (loc,) in session.query(IndustryJob.facility_id).distinct():
            if loc and loc > INT32_MAX:
                ids.add(loc)
        for (loc,) in session.query(IndustryJob.output_location_id).distinct():
            if loc and loc > INT32_MAX:
                ids.add(loc)
    return ids

def fetch_structure_info(structure_id: int, token: str) -> Optional[dict]:
    """Fetch structure details."""
    url = f"{ESI_BASE}/universe/structures/{structure_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, params=DATASOURCE)

    if resp.ok:
        return resp.json()
    logger.warning(f"[MarketStructure] Failed fetching info for structure {structure_id}: {resp.status_code}")
    return None

def fetch_structure_market(structure_id: int, token: str) -> list:
    """Fetch all market orders inside a structure."""
    url = f"{ESI_BASE}/markets/structures/{structure_id}/"
    orders = []
    page = 1

    while True:
        params = {**DATASOURCE, "page": page}
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code in (403, 404):
            return []

        resp.raise_for_status()
        batch = resp.json() or []
        orders.extend(batch)

        if "x-pages" not in resp.headers or page >= int(resp.headers["x-pages"]):
            break
        page += 1

    return orders

# ──────── Core Discovery ───────────────────────────────────────────────────────

def discover_structures(owner_id: int) -> None:
    """Discover all structures and identify market-enabled ones."""
    tokens = get_token(owner_id)
    char_tokens = list(tokens.items())

    private_ids = discover_private_structure_ids(owner_id)
    public_ids = fetch_public_structures()
    combined_ids = private_ids | public_ids

    logger.info(f"[MarketStructure] Scanning {len(combined_ids)} structure candidates...")

    market_structure_ids = []

    with get_db_session(owner_id=owner_id) as db:
        for sid in sorted(combined_ids):
            logger.info(f"[MarketStructure] ▶️ Scanning Structure {sid}")

            # Try fetching structure metadata
            structure_info = None
            for char_id, token in char_tokens:
                structure_info = fetch_structure_info(sid, token)
                if structure_info:
                    break

            if not structure_info:
                logger.warning(f"[MarketStructure] ⚪ Structure {sid} inaccessible")
                continue

            db.merge(Structure(
                structure_id=sid,
                name=structure_info.get("name"),
                owner_id=structure_info.get("owner_id"),
                solar_system_id=structure_info.get("solar_system_id"),
                type_id=structure_info.get("type_id"),
            ))
            db.commit()

            # Try fetching market orders
            for char_id, token in char_tokens:
                orders = fetch_structure_market(sid, token)
                if orders:
                    for order in orders:
                        db.merge(MarketOrder(
                            id=order["order_id"],
                            region_id=None,
                            type_id=order["type_id"],
                            price=order["price"],
                            volume=order.get("volume_remain", 0),
                            is_buy=order.get("is_buy_order", False),
                            location_id=sid,
                            last_seen=datetime.utcnow(),
                        ))
                    db.merge(MarketStructure(structure_id=sid))
                    db.commit()

                    market_structure_ids.append(sid)
                    logger.info(f"[MarketStructure] ✅ Market discovered at structure {sid}")
                    break

    update_config_yaml(market_structure_ids)

def update_config_yaml(market_structure_ids: list[int]) -> None:
    """Save discovered market structures into config.yaml cleanly."""
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    cfg.setdefault("Environment Variables", {})
    cfg["Market Structures"] = sorted(market_structure_ids)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, default_flow_style=False, sort_keys=False)

    logger.info(f"[MarketStructure] Updated {CONFIG_PATH} with {len(market_structure_ids)} market structures")
