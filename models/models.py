from datetime import datetime
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field
from bson import ObjectId

# Custom ObjectID field for pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectID")
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Base model with common fields
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime     = Field(default_factory=datetime.now)
    updated_at: datetime     = Field(default_factory=datetime.now)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed        = True
        json_encoders                  = {ObjectId: str}

# Player Model
class PlayerMMR(BaseModel):
    doubles: Optional[float]  = 0.0
    standard: Optional[float] = 0.0
    duel: Optional[float]     = 0.0

class Player(MongoBaseModel):
    ballchasing_id: Optional[str]  = None
    name: str
    platform: str
    platform_id: str
    discord_id: Optional[str]       = None
    discord_username: Optional[str] = None
    discord_avatar: Optional[str]   = None
    mmr: PlayerMMR = Field(default_factory=PlayerMMR)
    active: bool = True
    teams: List[PyObjectId] = []

# Team model
class Team(MongoBaseModel):
    name: str
    tag: str
    logo_url: Optional[str]       = None
    active: bool                  = True
    players: List[PyObjectId]     = []
    captain: Optional[PyObjectId] = None
    seasons: List[PyObjectId]     = []

# Season model
class Season(MongoBaseModel):
    name: str
    start_date: datetime
    end_date: Optional[datetime]          = None
    active: bool                          = True
    ballchasing_group_id: Optional[str]   = None
    ballchasing_group_link: Optional[str] = None
    teams: List[PyObjectId]               = []
    matches: List[PyObjectId]             = []

# Match model
class Match(MongoBaseModel):
    ballchasing_id: Optional[str] = None
    season: PyObjectId
    date: datetime
    team_blue: PyObjectId
    team_orange: PyObjectId
    score_blue: int               = 0
    score_orange: int             = 0
    winner: Optional[PyObjectId]  = None
    games: List[PyObjectId]       = []

# Team stats for a game
class TeamStats(BaseModel):
    goals: int   = 0
    shots: int   = 0
    saves: int   = 0
    assists: int = 0

# Game model
class Game(MongoBaseModel):
    ballchasing_id: Optional[str]    = None
    match: PyObjectId
    map: str
    duration: int  # in seconds
    blue_players: List[PyObjectId]   = []
    orange_players: List[PyObjectId] = []
    score_blue: int                  = 0
    score_orange: int                = 0
    winner: str  # "blue" or "orange"
    stats: Dict[str, TeamStats]      = Field(default_factory=lambda: {
        "blue": TeamStats(),
        "orange": TeamStats()
    })
    replay_url: Optional[str]        = None

# Player stats for a game
class PlayerBoostStats(BaseModel):
    bpm: float  = 0.0  # boost per minute
    avg: float  = 0.0  # average boost
    stolen: int = 0  # amount stolen

class PlayerMovementStats(BaseModel):
    avg_speed: float       = 0.0
    total_distance: float  = 0.0
    time_supersonic: float = 0.0
    time_ground: float     = 0.0
    time_air: float        = 0.0

class PlayerPositioningStats(BaseModel):
    time_defensive_half: float = 0.0
    time_offensive_half: float = 0.0
    time_behind_ball: float    = 0.0
    time_infront_ball: float   = 0.0

class PlayerStats(MongoBaseModel):
    player: PyObjectId
    game: PyObjectId
    team: str  # "blue" or "orange"
    goals: int                          = 0
    assists: int                        = 0
    saves: int                          = 0
    shots: int                          = 0
    score: int                          = 0
    dominane_quotient: float            = 0.0
    mvp: bool                           = False
    boost: PlayerBoostStats             = Field(default_factory=PlayerBoostStats)
    movement: PlayerMovementStats       = Field(default_factory=PlayerMovementStats)
    positioning: PlayerPositioningStats = Field(default_factory=PlayerPositioningStats)

# Tournament model
class Tournament(MongoBaseModel):
    name: str
    organizer: str
    start_date: datetime
    end_date: Optional[datetime] = None
    prize_pool: float            = 0.0
    format: str  # "single_elimination", "double_elimination", "round_robin", etc.
    teams: List[PyObjectId]      = []
    matches: List[PyObjectId]    = []
    winner: Optional[PyObjectId] = None

# BallchasingSync model
class BallchasingSync(MongoBaseModel):
    last_sync: datetime    = Field(default_factory=datetime.utcnow)
    sync_type: str  # "players", "matches", "replays", etc.
    status: str  # "success", "failed", "in_progress"
    details: Optional[str] = None

# Add to models.py
class PlayerTransfer(MongoBaseModel):
    player: PyObjectId  # Reference to Player document
    from_team: Optional[PyObjectId] = None  # Reference to Team document (None if new player)
    to_team: Optional[PyObjectId] = None  # Reference to Team document (None if player left the league)
    season: PyObjectId  # Reference to Season document
    transfer_date: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = None  # Optional reason for the transfer
    processed_by: Optional[str] = None 