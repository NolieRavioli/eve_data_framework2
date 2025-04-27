# db/database.py

import os
import sqlite3
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from db.models import Base

# ──────── Globals ─────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

PRIVATE_DATA_FOLDER = os.getenv("EVE_PRIVATE_DATABASE_FOLDER", "_privateData")
PUBLIC_DATABASE_FILE = os.getenv("EVE_PUBLIC_DATABASE_FILE", os.path.join("_publicData", "public.db"))

# Public DB internals
_public_engine = None
_PublicSession = None

# ──────── Public Database ─────────────────────────────────────────────────────

def initialize_public_database():
    """Initialize the public database connection if needed."""
    global _public_engine, _PublicSession

    if _public_engine is None:
        abs_path = os.path.abspath(PUBLIC_DATABASE_FILE).replace("\\", "/")
        db_url = f"sqlite:///{abs_path}"
        _public_engine = create_engine(db_url, echo=False, future=True)
        _PublicSession = sessionmaker(bind=_public_engine)
        logger.info(f"[PublicDB] Initialized public database at {abs_path}")

def get_public_session():
    """Return a new session for the public database."""
    if _PublicSession is None:
        initialize_public_database()
    return _PublicSession()

def create_public_tables():
    """Create tables on the public database."""
    if _public_engine is None:
        initialize_public_database()
    Base.metadata.create_all(_public_engine)
    logger.info("[PublicDB] Tables created.")

def raw_sqlite_connection():
    """Open a raw connection to the public SQLite database."""
    abs_path = os.path.abspath(PUBLIC_DATABASE_FILE)
    return sqlite3.connect(abs_path)

# ──────── Private Toon Databases ──────────────────────────────────────────────

def get_private_session(owner_id: int):
    """Return a new session for a toon-specific private database."""
    toon_folder = os.path.join(PRIVATE_DATA_FOLDER, str(owner_id))
    toon_db_path = os.path.join(toon_folder, f"{owner_id}.db")

    abs_path = os.path.abspath(toon_db_path).replace("\\", "/")
    db_url = f"sqlite:///{abs_path}"

    engine = create_engine(db_url, echo=False, future=True)
    Session = sessionmaker(bind=engine)

    logger.debug(f" Connected to database at {abs_path}")

    return Session()
print("[DB] get_private_session defined ✅")

def create_private_tables(character_id: int):
    """Create tables in a character's private database."""
    toon_folder = os.path.join(PRIVATE_DATA_FOLDER, str(character_id))
    toon_db_path = os.path.join(toon_folder, f"{character_id}.db")

    abs_path = os.path.abspath(toon_db_path).replace("\\", "/")
    db_url = f"sqlite:///{abs_path}"

    engine = create_engine(db_url, echo=False, future=True)
    Base.metadata.create_all(engine)
    logger.info(f"[PrivateDB] Tables created for toon {character_id}.")
