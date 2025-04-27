# fetchers/private/personal_industry_jobs.py

import requests
import logging
from datetime import datetime

from util.utils import get_token
from db.database import get_private_session
from db.models import IndustryJob

logger = logging.getLogger(__name__)

ESI = "https://esi.evetech.net/latest"

# ──────── Fetching ─────────────────────────────────────────────────────────────

def fetch_industry_jobs(char_id: int, access_token: str) -> list:
    """Fetch active industry jobs for a character."""
    url = f"{ESI}/characters/{char_id}/industry/jobs/"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

# ──────── Storage ───────────────────────────────────────────────────────────────

def store_jobs(owner_id: int, char_id: int, jobs: list):
    """Store industry jobs for a character into their owner's private DB."""
    db = get_private_session(owner_id)

    for job in jobs:
        db.merge(IndustryJob(
            job_id                = job["job_id"],
            character_id          = char_id,
            activity_id           = job["activity_id"],
            blueprint_id          = job["blueprint_id"],
            blueprint_location_id = job["blueprint_location_id"],
            blueprint_type_id     = job["blueprint_type_id"],
            cost                  = job.get("cost", 0.0),
            duration              = job["duration"],
            facility_id           = job["facility_id"],
            installer_id          = job["installer_id"],
            licensed_runs         = job.get("licensed_runs", 0),
            output_location_id    = job["output_location_id"],
            runs                  = job["runs"],
            status                = job["status"],
            start_date            = datetime.fromisoformat(job["start_date"].replace("Z", "+00:00")),
            end_date              = datetime.fromisoformat(job["end_date"].replace("Z", "+00:00")),
        ))

    db.commit()
    db.close()

# ──────── Orchestrator ───────────────────────────────────────────────────────────

def fetch_all_industry(owner_id: int):
    """Fetch and store industry jobs for all characters owned by the given owner."""
    tokens = get_token(owner_id)

    for char_id, token_row in tokens.items():
        logger.info(f"[fetch_all_industry] Fetching industry jobs for {char_id}")
        try:
            jobs = fetch_industry_jobs(char_id, token_row["access_token"])
            store_jobs(owner_id, char_id, jobs)
            logger.info(f"[fetch_all_industry] Stored {len(jobs)} jobs for {char_id}")
        except Exception as e:
            logger.error(f"[fetch_all_industry] Failed fetching jobs for {char_id}: {e}")
