# util/skills.py

import logging
from db.database import get_private_session
from db.models import IngameSkillState

logger = logging.getLogger(__name__)

# EVE skill IDs for relevant job queue expansions
MASS_PRODUCTION_ID = 3387
ADV_MASS_PRODUCTION_ID = 24625
LAB_OPERATION_ID = 3406
ADV_LAB_OPERATION_ID = 24624

def get_industry_queues(owner_id: int, character_id: int) -> dict:
    """
    Return the max manufacturing and science job slots based on accurate in-game usable skill levels.
    Format: { "manuf": int, "science": int }
    """
    with get_private_session(owner_id) as db:
        skills = {
            s.skill_id: s.current_level
            for s in db.query(IngameSkillState).filter_by(character_id=character_id)
        }

        logger.debug(f"[Skills] Usable skills for {character_id}: {skills}")

        manuf_slots = 1 + skills.get(MASS_PRODUCTION_ID, 0) + skills.get(ADV_MASS_PRODUCTION_ID, 0)
        science_slots = 1 + skills.get(LAB_OPERATION_ID, 0) + skills.get(ADV_LAB_OPERATION_ID, 0)

        return {
            "manuf": manuf_slots,
            "science": science_slots,
        }
