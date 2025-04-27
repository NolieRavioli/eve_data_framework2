# db/toon_map.py

import os
import sqlite3
import logging

# ──────── Setup ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
PUBLIC_DB = os.getenv("EVE_PUBLIC_DATABASE_FILE", "_publicData/public.db")

# ──────── Toon Mapping Utilities ─────────────────────────────────────────────

def ensure_user_toons_table():
    """Ensure the 'user_toons' table exists in the public database."""
    with sqlite3.connect(PUBLIC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_toons (
                character_id INTEGER PRIMARY KEY,
                owner_id INTEGER
            )
        """)
        conn.commit()
    logger.debug("[ToonMap] Ensured user_toons table exists.")

def insert_user_toon(character_id: int, owner_id: int):
    """Insert or update a character-to-owner mapping."""
    ensure_user_toons_table()
    with sqlite3.connect(PUBLIC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_toons (character_id, owner_id)
            VALUES (?, ?)
        """, (character_id, owner_id))
        conn.commit()
    logger.info(f"[ToonMap] Mapped character {character_id} → owner {owner_id}")

def get_linked_toons(owner_id: int) -> list:
    """Return a list of character IDs linked to a specific owner."""
    ensure_user_toons_table()
    with sqlite3.connect(PUBLIC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT character_id FROM user_toons WHERE owner_id = ?
        """, (owner_id,))
        results = cursor.fetchall()
    toon_list = [row[0] for row in results]
    logger.debug(f"[ToonMap] Found {len(toon_list)} toons linked to owner {owner_id}")
    return toon_list

def get_owner_for_character(character_id: int) -> int:
    """Given a character ID, return the associated owner ID."""
    ensure_user_toons_table()
    with sqlite3.connect(PUBLIC_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT owner_id FROM user_toons WHERE character_id = ?
        """, (character_id,))
        result = cursor.fetchone()
    if result:
        logger.debug(f"[ToonMap] Owner {result[0]} found for character {character_id}")
        return result[0]
    logger.warning(f"[ToonMap] No owner found for character {character_id}")
    raise ValueError(f"No owner found for character {character_id}")
