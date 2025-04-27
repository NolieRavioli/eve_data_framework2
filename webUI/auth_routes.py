# webUI/auth_routes.py

import os
import json
import logging
from flask import Blueprint, redirect, request, session, url_for
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
import jwt

from util.auth import CredentialManager, TokenDBManager, SSOManager
from db.toon_map import insert_user_toon, get_owner_for_character
from db.db_initializer import initialize_private_database

# ──────── Globals ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)
AUTH_URL = "https://login.eveonline.com/v2/oauth/authorize"
TOKEN_URL = "https://login.eveonline.com/v2/oauth/token"

# ──────── Routes ──────────────────────────────────────────────────────────────

@auth_bp.route("/login")
def login():
    """Login route — initiate SSO authentication."""
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    client_id, client_secret, redirect_uri, scopes = CredentialManager.load_credentials()
    eve = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes.split())
    auth_url, state = eve.authorization_url(AUTH_URL)
    session['oauth_state'] = state
    return redirect(auth_url)

@auth_bp.route("/add_toon")
def add_toon():
    """Add toon route — allow linking additional characters."""
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    client_id, client_secret, redirect_uri, scopes = CredentialManager.load_credentials()
    eve = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes.split())
    auth_url, state = eve.authorization_url(AUTH_URL)
    session['oauth_state'] = state
    session['add_toon'] = True
    return redirect(auth_url)

@auth_bp.route("/callback")
def callback():
    """Callback route — handle SSO response."""
    client_id, client_secret, redirect_uri, scopes = CredentialManager.load_credentials()
    state = session.pop('oauth_state', None)
    if not state:
        return "Session expired or missing state.", 400

    is_add_toon = session.pop('add_toon', False)
    eve = OAuth2Session(client_id, redirect_uri=redirect_uri, state=state)

    try:
        token = eve.fetch_token(
            TOKEN_URL,
            authorization_response=request.url,
            auth=HTTPBasicAuth(client_id, client_secret)
        )

        decoded = jwt.decode(token['access_token'], options={"verify_signature": False})
        char_id = int(decoded['sub'].split(':')[-1])

        if is_add_toon:
            logger.info(f"[Auth] ADD TOON flow detected for {char_id}")
            owner_id = session.get('owner_id', char_id)

            # Make sure the private DB exists
            db_path = TokenDBManager.find_user_db(owner_id)
            if not db_path:
                return "Error: Could not find private DB for owner.", 500

            token_db = TokenDBManager(owner_id)  # <--- Token manager for the new character
            token_db.save_tokens(
                char_id,
                token['access_token'],
                token['refresh_token'],
                token['expires_at'],
                token.get('scope', '')
            )

            insert_user_toon(character_id=char_id, owner_id=owner_id)
            return redirect(url_for("dashboard.home"))

        else:
            logger.info(f"[Auth] NORMAL LOGIN flow detected for {char_id}")

            try:
                owner_id = get_owner_for_character(char_id)
                logger.info(f"[Auth] Found existing owner {owner_id} for toon {char_id}")
            except ValueError:
                owner_id = char_id
                insert_user_toon(character_id=char_id, owner_id=owner_id)
                logger.info(f"[Auth] Created new owner {owner_id} for toon {char_id}")

            db_path = TokenDBManager.find_user_db(owner_id)
            if not db_path:
                TokenDBManager(owner_id)  # Create new private DB
                logger.info(f"[Auth] Created private DB for owner {owner_id}")

            TokenDBManager(owner_id).save_tokens(
                char_id,
                access_token=token["access_token"],
                refresh_token=token["refresh_token"],
                expires_at=token["expires_at"],
                scopes=token.get("scope", "")
            )

            session["character_id"] = char_id
            session["owner_id"] = owner_id
            session["access_token"] = token["access_token"]
            session["refresh_token"] = token["refresh_token"]

            initialize_private_database(owner_id)

        return redirect(url_for("dashboard.home"))

    except Exception as e:
        logger.exception("[Auth] Error during token exchange")
        return f"Authentication failed: {e}", 500

@auth_bp.route("/logout")
def logout():
    """Logout route — clear session and redirect to home."""
    session.clear()
    return redirect(url_for("dashboard.home"))
