# db/db_initializer.py

import os
import logging
from sqlalchemy import create_engine
from db.models import Base, PrivateBase

# ──────── Logger ────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ──────── Constants ─────────────────────────────────────────────────────────────
PUBLIC_DB_PATH = os.getenv("EVE_PUBLIC_DATABASE_FILE", "_publicData/public.db")
PRIVATE_DATA_FOLDER = os.getenv("EVE_PRIVATE_DATABASE_FOLDER", "_privateData")

# ──────── Public Database Initialization ────────────────────────────────────────

def initialize_public_database():
    """Initialize the public (shared) database and create tables."""
    abs_path = os.path.abspath(PUBLIC_DB_PATH).replace("\\", "/")
    engine = create_engine(f"sqlite:///{abs_path}", future=True)
    Base.metadata.create_all(engine)
    logger.info(f"[DBInitializer] Public database initialized at {abs_path}")

# ──────── Private Database Initialization ───────────────────────────────────────

def initialize_private_database(owner_id: int):
    """Initialize a private (toon-specific) database."""
    toon_folder = os.path.join(PRIVATE_DATA_FOLDER, str(owner_id))
    os.makedirs(toon_folder, exist_ok=True)

    private_db_path = os.path.join(toon_folder, f"{owner_id}.db")
    abs_path = os.path.abspath(private_db_path).replace("\\", "/")

    engine = create_engine(f"sqlite:///{abs_path}", future=True)
    PrivateBase.metadata.create_all(engine)
    logger.info(f"[DBInitializer] Private database initialized for owner {owner_id} at {abs_path}")

# ──────── Full System Initialization ────────────────────────────────────────────

def initialize_all(owner_id: int):
    """Initialize both public and private databases."""
    initialize_public_database()
    initialize_private_database(owner_id)
    logger.info(f"[DBInitializer] Full initialization completed for owner {owner_id}.")
