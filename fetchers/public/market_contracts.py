# fetchers/public/market_contracts.py

import logging
from datetime import datetime
import requests

from db.database import get_public_session
from db.models import PublicContract
from util.utils import get_all_region_ids

# ──────── Globals ───────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
ESI = "https://esi.evetech.net/latest"

# ──────── Fetching ──────────────────────────────────────────────────────────────

def fetch_public_contracts(region_id: int) -> list[dict]:
    """Fetch all public contracts in a region, handling pagination."""
    all_contracts = []
    page = 1
    url = f"{ESI}/contracts/public/{region_id}/"

    while True:
        resp = requests.get(url, params={"page": page})
        if resp.status_code == 204:
            logger.info(f"[Contracts] Region {region_id}: no contracts (204) on page {page}")
            break

        resp.raise_for_status()
        page_data = resp.json()

        if not page_data:
            logger.info(f"[Contracts] Region {region_id}: empty page {page}, stopping early")
            break

        all_contracts.extend(page_data)
        total_pages = int(resp.headers.get("X-Pages", page))

        logger.info(f"[Contracts] Region {region_id}: fetched page {page}/{total_pages}")

        if page >= total_pages:
            break
        page += 1

    return all_contracts

# ──────── Storage ───────────────────────────────────────────────────────────────

def store_contracts(region_id: int, contracts: list[dict]) -> None:
    """Merge a list of contract dicts into the database."""
    with get_public_session() as db:
        for contract in contracts:
            db.merge(PublicContract(
                id=contract["contract_id"],
                region_id=region_id,
                type=contract["type"],
                price=contract.get("price", 0.0),
                volume=contract.get("volume", 0.0),
                date_issued=datetime.fromisoformat(
                    contract["date_issued"].replace("Z", "+00:00")
                ),
            ))
        db.commit()
    logger.info(f"[Contracts] Region {region_id}: stored {len(contracts)} contracts")

# ──────── Orchestration ──────────────────────────────────────────────────────────

def fetch_all_public_contracts() -> None:
    """Fetch and store public contracts for every EVE region."""
    logger.info("[Contracts] Starting full public contracts fetch")
    region_ids = get_all_region_ids()

    for region_id in region_ids:
        try:
            logger.info(f"[Contracts] === Region {region_id} ===")
            contracts = fetch_public_contracts(region_id)
            if contracts:
                store_contracts(region_id, contracts)
        except Exception as e:
            logger.exception(f"[Contracts] Failed fetching region {region_id}: {e}")

    logger.info("[Contracts] Completed fetching all public contracts")
