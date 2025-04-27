# fetchers/private/personal_skills.py

import requests
import logging
from datetime import datetime

from db.database import get_private_session
from db.models import SkillRaw, SkillQueueEntry, IngameSkillState
from util.utils import get_token

logger = logging.getLogger(__name__)

ESI = "https://esi.evetech.net/latest"

# ──────── Fetching ─────────────────────────────────────────────────────────────

def fetch_skills(char_id: int, access_token: str) -> list:
    """Fetch all skills for a character."""
    url = f"{ESI}/characters/{char_id}/skills/"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("skills", [])

def fetch_skillqueue(char_id: int, access_token: str) -> list:
    """Fetch skill queue for a character."""
    url = f"{ESI}/characters/{char_id}/skillqueue/"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

# ──────── Storage ───────────────────────────────────────────────────────────────

def store_skill_data(owner_id: int, char_id: int, raw_skills: list, queue: list):
    """Store skills and skill queue into owner's private database."""
    db = get_private_session(owner_id)

    db.query(SkillRaw).filter_by(character_id=char_id).delete()
    db.query(SkillQueueEntry).filter_by(character_id=char_id).delete()
    db.query(IngameSkillState).filter_by(character_id=char_id).delete()

    raw_map = {}
    for skill in raw_skills:
        db.add(SkillRaw(
            character_id=char_id,
            skill_id=skill["skill_id"],
            active_level=skill["active_skill_level"],
            skillpoints_in_skill=skill["skillpoints_in_skill"],
            trained_skill_level=skill["trained_skill_level"],
            skill_active=skill.get("active", True),
        ))
        raw_map[skill["skill_id"]] = skill

    for entry in queue:
        finish_time = datetime.fromisoformat(entry["finish_date"].replace("Z", "+00:00")) if "finish_date" in entry else None
        db.add(SkillQueueEntry(
            character_id=char_id,
            queue_position=entry["queue_position"],
            skill_id=entry["skill_id"],
            finish_level=entry["finished_level"],
            finish_date=finish_time,
        ))

    for sid, skill in raw_map.items():
        db.add(IngameSkillState(
            character_id=char_id,
            skill_id=sid,
            current_level=skill["active_skill_level"],
            is_in_training=False,
            training_finishes_at=None
        ))

    db.commit()
    db.close()

# ──────── Orchestrator ───────────────────────────────────────────────────────────

def fetch_all_skills(owner_id: int):
    """Fetch and store skills for all characters owned by the given owner."""
    tokens = get_token(owner_id)

    for char_id, token_row in tokens.items():
        logger.info(f"[fetch_all_skills] Fetching skills for {char_id}")
        try:
            raw_skills = fetch_skills(char_id, token_row["access_token"])
            queue = fetch_skillqueue(char_id, token_row["access_token"])
            store_skill_data(owner_id, char_id, raw_skills, queue)
            logger.info(f"[fetch_all_skills] Stored skills + queue + ingame state for {char_id}")
        except requests.HTTPError as e:
            logger.error(f"[fetch_all_skills] Error fetching skills for {char_id}: {e}")
