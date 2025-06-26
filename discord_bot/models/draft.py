from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DraftPick(BaseModel):
    """Represents a single draft pick"""
    pick_number: int
    player_id: str
    player_name: str
    original_rank: int
    odds: float = Field(default=0.0, description="Probability of being picked at this position")


class SeasonDraft(BaseModel):
    """Represents a draft lottery for a season"""
    id: Optional[str] = Field(None, alias="_id")
    season_id: str
    date: datetime = Field(default_factory=datetime.utcnow)
    completed: bool = Field(default=False)
    picks: List[DraftPick] = Field(default_factory=list)
    unpicked_players: List[str] = Field(default_factory=list)  # Player IDs
    
    # Player rankings used for the draft
    participant_rankings: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Odds table used (allows customization per season)
    odds_table: Optional[Dict[int, Dict[int, float]]] = None
    
    class Config:
        populate_by_name = True