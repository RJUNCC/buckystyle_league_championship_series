# File: main.py
import os
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
from datetime import datetime

from models.models import Player, Team, Season, Match, Game, PlayerStats, Tournament
from models.repositories import (
    PlayerRepository, TeamRepository, SeasonRepository, 
    MatchRepository, GameRepository, PlayerStatsRepository, 
    TournamentRepository
)
from scripts.ballchasing_service import BallchasingService

app = FastAPI(title="Rocket League Management System")

# Get repositories
def get_player_repo():
    return PlayerRepository()

def get_team_repo():
    return TeamRepository()

def get_season_repo():
    return SeasonRepository()

def get_match_repo():
    return MatchRepository()

def get_game_repo():
    return GameRepository()

def get_player_stats_repo():
    return PlayerStatsRepository()

def get_tournament_repo():
    return TournamentRepository()

def get_ballchasing_service():
    api_key = os.getenv("BALLCHASING_API_KEY")
    if not api_key:
        raise Exception("BALLCHASING_API_KEY environment variable not set")
    return BallchasingService(api_key)

# Player routes
@app.get("/players/", response_model=List[Player])
async def get_players(
    player_repo: PlayerRepository = Depends(get_player_repo)
):
    return await player_repo.get_all()

@app.get("/players/{player_id}", response_model=Player)
async def get_player(
    player_id: str,
    player_repo: PlayerRepository = Depends(get_player_repo)
):
    player = await player_repo.get(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@app.post("/players/", response_model=Player)
async def create_player(
    player: Player,
    player_repo: PlayerRepository = Depends(get_player_repo)
):
    return await player_repo.create(player)

# Team routes
@app.get("/teams/", response_model=List[Team])
async def get_teams(
    team_repo: TeamRepository = Depends(get_team_repo)
):
    return await team_repo.get_all()

@app.get("/teams/{team_id}", response_model=Team)
async def get_team(
    team_id: str,
    team_repo: TeamRepository = Depends(get_team_repo)
):
    team = await team_repo.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team

@app.post("/teams/", response_model=Team)
async def create_team(
    team: Team,
    team_repo: TeamRepository = Depends(get_team_repo)
):
    return await team_repo.create(team)

# Season routes
@app.get("/seasons/", response_model=List[Season])
async def get_seasons(
    season_repo: SeasonRepository = Depends(get_season_repo)
):
    return await season_repo.get_all()

@app.get("/seasons/active", response_model=Season)
async def get_active_season(
    season_repo: SeasonRepository = Depends(get_season_repo)
):
    season = await season_repo.get_active()
    if not season:
        raise HTTPException(status_code=404, detail="No active season found")
    return season

@app.post("/seasons/", response_model=Season)
async def create_season(
    season: Season,
    season_repo: SeasonRepository = Depends(get_season_repo)
):
    return await season_repo.create(season)

# Ballchasing API routes
@app.post("/sync/replay/{replay_id}", response_model=Game)
async def sync_replay(
    replay_id: str,
    ballchasing_service: BallchasingService = Depends(get_ballchasing_service)
):
    try:
        return await ballchasing_service.sync_replay(replay_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)