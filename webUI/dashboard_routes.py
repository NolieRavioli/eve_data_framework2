# webUI/dashboard_routes.py

from flask import Blueprint, render_template, session
import logging
from db.database import get_private_session
from db.models import IndustryJob, WalletTransaction, Asset, Bookmark
from db.toon_map import get_linked_toons
from util.sde import name_from_id
from analysis.job_slots import analyze_slots

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/")
def home():
    """Landing page (dashboard if logged in, basic page if not)."""
    industry_jobs = []
    wallet_txns = []
    assets = []
    bookmarks = []
    linked_toons = []
    slot_status = []
    char_id = None
    owner_id = None
    logged_in = False

    if "character_id" in session and "owner_id" in session:
        char_id = session["character_id"]
        owner_id = session["owner_id"]
        logged_in = True

        logger.info(f"Loading dashboard for character {char_id}, owner {owner_id}")

        #try:
        linked_toons = get_linked_toons(owner_id)

        db = get_private_session(owner_id)

        industry_jobs = db.query(IndustryJob).filter_by(character_id=char_id).limit(10).all()
        wallet_txns = db.query(WalletTransaction).filter_by(character_id=char_id).limit(10).all()
        assets = db.query(Asset).filter_by(character_id=char_id).limit(50).all()  
        bookmarks = db.query(Bookmark).filter_by(character_id=char_id).limit(10).all()

        db.close()

        # Run slot analyzer and capture output
        slot_status = analyze_slots(owner_id)

        #except Exception as e:
            #logger.error(f"Error loading dashboard data: {e}")

    return render_template(
        "dashboard.html",
        industry_jobs=industry_jobs,
        wallet_txns=wallet_txns,
        assets=assets,
        bookmarks=bookmarks,
        logged_in=logged_in,
        char_id=char_id,
        owner_id=owner_id,
        linked_toons=linked_toons,
        slot_status=slot_status,
        name_from_id=name_from_id
    )
