# db/models.py

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base
import datetime

# ──────── Base Declarative Classes ───────────────────────────────────────────────
Base = declarative_base()
PrivateBase = declarative_base()

# ──────── Public Database Models ──────────────────────────────────────────────────

class SolarSystem(Base):
    __tablename__ = "systems"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    constellation_id = Column(Integer)
    region_id = Column(Integer)
    planets = Column(JSON)      # List of planet IDs
    moons = Column(JSON)        # List of moon IDs
    stargates = Column(JSON)    # List of stargate IDs
    security = Column(Float)
    solar_system_name_id = Column(Integer)
    neighbors = Column(JSON)    # List of connected system IDs
    
class Stargate(Base):
    __tablename__ = "stargates"
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer)
    system_id = Column(Integer)         # Solar system where the stargate is located
    destination_gate_id = Column(Integer)
    destination_system_id = Column(Integer)
    position = Column(JSON)             # [x, y, z]

class MarketOrder(Base):
    __tablename__ = "market_orders"
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer)
    type_id = Column(Integer)
    price = Column(Float)
    volume = Column(Float)
    is_buy = Column(Boolean)
    location_id = Column(Integer)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)

class RegionVolume(Base):
    __tablename__ = "region_volumes"
    region_id = Column(Integer, primary_key=True)
    volume = Column(Float)
    last_updated = Column(DateTime)

class TypeInfo(Base):
    __tablename__ = "type_info"
    type_id = Column(Integer, primary_key=True)
    name = Column(String)
    volume = Column(Float)

class UserToon(Base):
    __tablename__ = "user_toons"
    character_id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, index=True)

class PublicContract(Base):
    __tablename__ = "public_contracts"
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, index=True)
    type = Column(String)
    price = Column(Float)
    date_issued = Column(DateTime)
    volume = Column(Float)

class Structure(Base):
    __tablename__ = "structures"
    structure_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    owner_id = Column(Integer, nullable=True)
    solar_system_id = Column(Integer, nullable=True)
    region_id = Column(Integer, nullable=True)
    type_id = Column(Integer, nullable=True)

class MarketStructure(Base):
    __tablename__ = "market_structures"
    structure_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=True)
    owner_id = Column(Integer, nullable=True)
    solar_system_id = Column(Integer, nullable=True)
    region_id = Column(Integer, nullable=True)
    type_id = Column(Integer, nullable=True)

# ──────── Private Database Models ────────────────────────────────────────────────

class Token(PrivateBase):
    __tablename__ = "tokens"
    character_id = Column(Integer, primary_key=True)
    access_token = Column(String)
    refresh_token = Column(String)
    expires_at = Column(Float)
    scopes = Column(String)

class Asset(PrivateBase):
    __tablename__ = "assets"
    item_id = Column(BigInteger, primary_key=True)
    character_id = Column(Integer, index=True)
    type_id = Column(Integer)
    location_id = Column(Integer)
    quantity = Column(Integer)
    location_flag = Column(Integer)

class PersonalBookmark(PrivateBase):
    __tablename__ = "bookmarks"
    bookmark_id = Column(BigInteger, primary_key=True)
    character_id = Column(Integer, index=True)
    folder_id = Column(BigInteger)
    location_id = Column(BigInteger)
    item_id = Column(BigInteger)
    label = Column(String)
    created = Column(DateTime)
    coordinates = Column(JSON)
    notes = Column(String)

Bookmark = PersonalBookmark

class SkillRaw(PrivateBase):
    __tablename__ = "skill_raw"
    character_id = Column(Integer, primary_key=True)
    skill_id = Column(Integer, primary_key=True)
    active_level = Column(Integer)
    skillpoints_in_skill = Column(Integer)
    trained_skill_level = Column(Integer)
    skill_active = Column(Boolean)

class SkillQueueEntry(PrivateBase):
    __tablename__ = "skill_queue"
    character_id = Column(Integer, primary_key=True)
    queue_position = Column(Integer, primary_key=True)
    skill_id = Column(Integer)
    finish_level = Column(Integer)
    finish_date = Column(DateTime)

class IngameSkillState(PrivateBase):
    __tablename__ = "ingame_skill_levels"
    character_id = Column(Integer, primary_key=True)
    skill_id = Column(Integer, primary_key=True)
    current_level = Column(Integer)
    is_in_training = Column(Boolean)
    training_finishes_at = Column(DateTime, nullable=True)

class IndustryJob(PrivateBase):
    __tablename__ = "industry_jobs"
    job_id = Column(BigInteger, primary_key=True)
    character_id = Column(Integer, index=True)
    activity_id = Column(Integer)
    blueprint_id = Column(BigInteger)
    blueprint_location_id = Column(BigInteger)
    blueprint_type_id = Column(Integer)
    cost = Column(Float)
    duration = Column(Integer)
    facility_id = Column(BigInteger)
    installer_id = Column(BigInteger)
    licensed_runs = Column(Integer)
    output_location_id = Column(BigInteger)
    runs = Column(Integer)
    status = Column(String)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

class WalletTransaction(PrivateBase):
    __tablename__ = "wallet_transactions"
    id = Column(BigInteger, primary_key=True)
    character_id = Column(Integer, index=True)
    amount = Column(Float)
    date = Column(DateTime)
    ref_type = Column(String)
    context_id = Column(BigInteger)
    context_id_type = Column(Integer)
