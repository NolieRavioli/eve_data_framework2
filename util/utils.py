# util/utils.py

import os
import time
import logging
import sqlite3
import requests
import yaml
from util.auth import SSOManager, TokenDBManager
from db.database import get_private_session
from db.models import Token

logger = logging.getLogger(__name__)

CONFIG_PATH = "config.yaml"
PRIVATE_DATA_FOLDER = os.getenv("EVE_PRIVATE_DATABASE_FOLDER", "_privateData/")
ESI_BASE = "https://esi.evetech.net/latest"
HEADERS = {"Accept": "application/json"}
DATASOURCE = {"datasource": "tranquility"}

# ──────── Config Loader ─────────────────────────────────────────────────────────

def load_config(config_path: str = CONFIG_PATH) -> dict:
    """
    Loads Environment Variables from a config.yaml into os.environ.
    Returns the full config dict.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    env_vars = cfg.get("Environment Variables", {})
    if not isinstance(env_vars, dict):
        raise ValueError("Expected 'Environment Variables' to be a dictionary in config.yaml")

    for key, value in env_vars.items():
        if key not in os.environ:
            if isinstance(value, list):
                os.environ[key] = ",".join(str(v) for v in value)
            else:
                os.environ[key] = str(value)

    logger.info(f"Loaded {len(env_vars)} environment variables from {config_path}")
    return cfg

# ──────── Token / Character Utilities ───────────────────────────────────────────

def get_token(owner_id: int) -> dict:
    """
    Return { character_id: TokenRow } dict for all characters linked to an owner.
    If any tokens are expired, refresh them automatically and SAVE them.
    """
    token_map = {}
    now = time.time()
    session = get_private_session(owner_id)
    token_db = TokenDBManager(owner_id)
    try:
        tokens = session.query(Token).all()
        for token in tokens:
            if token.expires_at and token.expires_at < now:
                logger.info(f"[TokenManager] Token expired for {token.character_id}, refreshing...")
                try:
                    refreshed = SSOManager.refresh_token(token.refresh_token)
                    # Update the SQLAlchemy model
                    token.access_token = refreshed["access_token"]
                    token.refresh_token = refreshed["refresh_token"]
                    token.expires_at = refreshed.get("expires_at", now + refreshed.get("expires_in", 1200))
                    token.scopes = refreshed.get("scope", token.scopes)
                    # Save to SQLAlchemy (private toon db)
                    session.commit()
                    # Save to raw SQLite (token db)
                    token_db.save_tokens(
                        character_id=token.character_id,
                        access_token=token.access_token,
                        refresh_token=token.refresh_token,
                        expires_at=token.expires_at,
                        scopes=token.scopes,
                    )
                except Exception as e:
                    logger.error(f"[TokenManager] Failed to refresh token for {token.character_id}: {e}")
                    continue
            token_map[token.character_id] = {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_at": token.expires_at,
                "scopes": token.scopes,
            }
    finally:
        session.close()
    return token_map

def iter_characters(owner_id: int):
    """Yield character IDs from a user's private database."""
    db_path = os.path.join(PRIVATE_DATA_FOLDER, str(owner_id), f"{owner_id}.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"No private database found for owner {owner_id}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT character_id FROM tokens")
        for (character_id,) in cursor.fetchall():
            yield character_id
    finally:
        conn.close()

# ──────── ESI Utilities ──────────────────────────────────────────────────────────

def get_all_region_ids():
    """Get all region IDs from ESI."""
    url = f"{ESI_BASE}/universe/regions/"
    resp = requests.get(url, headers=HEADERS, params=DATASOURCE)
    resp.raise_for_status()
    return resp.json()

def is_structure(structure_id: int) -> bool:
    """Check if a given ID is a structure via ESI."""
    url = f"{ESI_BASE}/universe/structures/{structure_id}/"
    r = requests.get(url, headers=HEADERS, params=DATASOURCE)
    return r

def resolve_names_to_ids(names: list[str]) -> dict:
    """Bulk convert system or structure names to IDs using ESI."""
    if not names:
        return {}

    response = requests.post(
        f"{ESI_BASE}/universe/ids/",
        headers=HEADERS,
        params={"datasource": "tranquility", "language": os.getenv("LANGUAGE", "en")},
        json=names,
    )
    response.raise_for_status()

    systems = response.json().get("systems", [])
    return {entry["name"]: entry["id"] for entry in systems}
