# util/auth.py

import os
import json
import time
import shutil
import sqlite3
import requests
import logging
from typing import Optional, Tuple
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from cryptography.fernet import Fernet
from ruamel.yaml import YAML
import jwt
from jwt import decode, get_unverified_header
from jwt.algorithms import RSAAlgorithm

# ─────── Globals ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

PRIVATE_DATA_FOLDER = os.getenv("PRIVATE_DATA_PATH", "_privateData")
PUBLIC_DATA_FOLDER = os.getenv("PUBLIC_DATA_PATH", "_publicData")
CONFIG_FILE_PATH = os.getenv("CONFIG_FILE", "config.yaml")

CLIENT_CRED_FILE = os.path.join(PUBLIC_DATA_FOLDER, "client_cred")
KEY_FILE = os.path.join(PUBLIC_DATA_FOLDER, "key")
JWKS_CACHE = os.path.join(PUBLIC_DATA_FOLDER, "jwks.json")

TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"
AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"

# ─────── Utility Functions ───────────────────────────────────────────────────
def ensure_folder(path: str):
    os.makedirs(path, exist_ok=True)

def get_encryption_key() -> Fernet:
    """Load or create encryption key."""
    ensure_folder(PUBLIC_DATA_FOLDER)
    if not os.path.exists(KEY_FILE):
        with open(KEY_FILE, "wb") as f:
            f.write(Fernet.generate_key())
    with open(KEY_FILE, "rb") as f:
        return Fernet(f.read())

# ─────── Classes ─────────────────────────────────────────────────────────────
class CredentialManager:
    """Handles loading and saving client credentials."""
    @staticmethod
    def load_credentials() -> Tuple[str, str, str, str]:
        fernet = get_encryption_key()

        if not os.path.exists(CLIENT_CRED_FILE):
            logger.info("[CredentialManager] No credentials found. Setup required.")
            return CredentialManager.setup_credentials(fernet)

        with open(CLIENT_CRED_FILE, "rb") as f:
            creds = json.loads(fernet.decrypt(f.read()).decode())
            return creds["client_id"], creds["client_secret"], creds["redirect_uri"], creds["scopes"]

    @staticmethod
    def setup_credentials(fernet: Fernet) -> Tuple[str, str, str, str]:
        import webbrowser
        webbrowser.open("https://developers.eveonline.com/applications")
        client_id = input("Client ID: ").strip()
        client_secret = input("Client Secret: ").strip()
        redirect_uri = input("Callback URL: ").strip()
        raw_scopes = input("Scopes (JSON list format): ").strip()

        try:
            scopes_list = json.loads(raw_scopes)
            scopes = " ".join(scopes_list)
        except Exception:
            raise ValueError("Scopes must be a valid JSON list!")

        creds = {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scopes": scopes
        }

        ensure_folder(PUBLIC_DATA_FOLDER)
        with open(CLIENT_CRED_FILE, "wb") as f:
            f.write(fernet.encrypt(json.dumps(creds).encode()))
        logger.info(f"[CredentialManager] Credentials saved at {CLIENT_CRED_FILE}")

        return client_id, client_secret, redirect_uri, scopes

class TokenDBManager:
    """Handles SQLite token operations (per owner_id)."""

    def __init__(self, owner_id: int):
        self.owner_id = owner_id
        self.folder = os.path.join(PRIVATE_DATA_FOLDER, str(owner_id))
        ensure_folder(self.folder)
        self.db_path = os.path.join(self.folder, f"{owner_id}.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                character_id INTEGER PRIMARY KEY,
                access_token TEXT,
                refresh_token TEXT,
                expires_at REAL,
                scopes TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                character_id INTEGER PRIMARY KEY
            )
        """)
        conn.commit()
        conn.close()

    def save_tokens(self, character_id: int, access_token: str, refresh_token: str, expires_at: float, scopes: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO tokens (character_id, access_token, refresh_token, expires_at, scopes)
            VALUES (?, ?, ?, ?, ?)
        """, (character_id, access_token, refresh_token, expires_at, scopes))
        cursor.execute("""
            INSERT OR IGNORE INTO characters (character_id) VALUES (?)
        """, (character_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def find_user_db(owner_id: int) -> Optional[str]:
        path = os.path.join(PRIVATE_DATA_FOLDER, str(owner_id), f"{owner_id}.db")
        return path if os.path.exists(path) else None

class SSOManager:
    """Manages EVE SSO authentication flows."""

    @staticmethod
    def refresh_token(refresh_token: str) -> dict:
        client_id, client_secret, _, _ = CredentialManager.load_credentials()
        r = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret
            }
        )
        r.raise_for_status()
        token_data = r.json()
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 1200)
        return token_data

    @staticmethod
    def validate_token(token: str, refresh_token: str) -> str:
        if os.path.exists(JWKS_CACHE):
            with open(JWKS_CACHE, "r") as f:
                jwks = json.load(f)
        else:
            jwks = requests.get("https://login.eveonline.com/oauth/jwks").json()
            ensure_folder(PUBLIC_DATA_FOLDER)
            with open(JWKS_CACHE, "w") as f:
                json.dump(jwks, f)

        try:
            kid = get_unverified_header(token)["kid"]
            key = next(RSAAlgorithm.from_jwk(json.dumps(k)) for k in jwks["keys"] if k["kid"] == kid)
            decode(token, key, algorithms=["RS256"], audience="EVE Online", options={"verify_exp": True})
            return token
        except Exception:
            refreshed = SSOManager.refresh_token(refresh_token)
            return refreshed["access_token"]

class ConfigUpdater:
    """Manages config.yaml updates safely."""
    @staticmethod
    def safe_update_config(character_id: int, character_name: str = "Unknown Name"):
        yaml_loader = YAML()
        yaml_loader.preserve_quotes = True

        if os.path.exists(CONFIG_FILE_PATH):
            shutil.copy2(CONFIG_FILE_PATH, CONFIG_FILE_PATH + ".bak")

        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                cfg = yaml_loader.load(f) or {}
        except FileNotFoundError:
            cfg = {}

        if "characters" not in cfg:
            cfg["characters"] = {}

        str_id = str(character_id)
        if str_id not in cfg["characters"]:
            cfg["characters"][str_id] = character_name
            logger.info(f"[ConfigUpdater] Added character {character_id} to config.")
        else:
            logger.info(f"[ConfigUpdater] Character {character_id} already exists, skipping.")

        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            yaml_loader.dump(cfg, f)
