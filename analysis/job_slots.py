# analysis/job_slots.py

import logging
from datetime import datetime, timezone
from db.database import get_private_session
from db.models import IndustryJob
from fetchers.private.personal_skills import fetch_all_skills
from fetchers.private.personal_industry_jobs import fetch_all_industry
from util.utils import iter_characters
from util.skills import get_industry_queues

logger = logging.getLogger(__name__)

SCIENCE_ACTIVITY_IDS = {3, 4, 5, 7, 8}

def analyze_slots(owner_id: int) -> list:
    """Analyze active industry jobs and slot usage for all toons owned by owner_id."""
    now = datetime.now(timezone.utc)
    status_list = []

    with get_private_session(owner_id) as db:
        for char_id in iter_characters(owner_id):
            jobs = db.query(IndustryJob).filter_by(character_id=char_id).all()
            queues = get_industry_queues(owner_id, char_id)  # <-- Small fix: queues only need char_id

            def to_utc_aware(dt):
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

            manuf_jobs = [j for j in jobs if j.activity_id == 1 and to_utc_aware(j.end_date) > now]
            science_jobs = [j for j in jobs if j.activity_id in SCIENCE_ACTIVITY_IDS and to_utc_aware(j.end_date) > now]

            def summarize(job_list, max_slots, label):
                used = len(job_list)
                if used < max_slots:
                    msg = f"{char_id} — OPEN {label.upper()} SLOTS ({used}/{max_slots})"
                    logger.info(msg)
                    status_list.append(msg)
                else:
                    soonest = min(to_utc_aware(j.end_date) for j in job_list)
                    remaining = soonest - now
                    hours, remainder = divmod(remaining.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    msg = (
                        f"{char_id} — All {label} slots filled ({used}/{max_slots}), "
                        f"{int(hours)} hr {int(minutes)} min {int(seconds)} sec until next opening."
                    )
                    logger.info(msg)
                    status_list.append(msg)

            summarize(manuf_jobs, queues["manuf"], "manufacturing")
            summarize(science_jobs, queues["science"], "science")

    return status_list
