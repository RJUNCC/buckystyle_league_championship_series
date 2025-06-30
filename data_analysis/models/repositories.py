# File: repositories.py
from database import BaseRepository
from models import Player, Team, Season, Match, Game, PlayerStats, Tournament, BallchasingSync
from bson import ObjectId

class PlayerRepository(BaseRepository[Player]):
    def __init__(self):
        super().__init__(Player, "players")
    
    async def find_by_ballchasing_id(self, ballchasing_id: str) -> Player:
        players = await self.find({"ballchasing_id": ballchasing_id})
        return players[0] if players else None
    
    async def find_by_platform_id(self, platform: str, platform_id: str) -> Player:
        players = await self.find({"platform": platform, "platform_id": platform_id})
        return players[0] if players else None

class TeamRepository(BaseRepository[Team]):
    def __init__(self):
        super().__init__(Team, "teams")
    
    async def find_by_name(self, name: str) -> Team:
        teams = await self.find({"name": name})
        return teams[0] if teams else None

class SeasonRepository(BaseRepository[Season]):
    def __init__(self):
        super().__init__(Season, "seasons")
    
    async def get_active(self) -> Season:
        seasons = await self.find({"active": True})
        return seasons[0] if seasons else None

class MatchRepository(BaseRepository[Match]):
    def __init__(self):
        super().__init__(Match, "matches")
    
    async def find_by_season(self, season_id: str) -> list[Match]:
        return await self.find({"season": ObjectId(season_id)})
    
    async def find_by_ballchasing_id(self, ballchasing_id: str) -> Match:
        matches = await self.find({"ballchasing_id": ballchasing_id})
        return matches[0] if matches else None

class GameRepository(BaseRepository[Game]):
    def __init__(self):
        super().__init__(Game, "games")
    
    async def find_by_match(self, match_id: str) -> list[Game]:
        return await self.find({"match": ObjectId(match_id)})
    
    async def find_by_ballchasing_id(self, ballchasing_id: str) -> Game:
        games = await self.find({"ballchasing_id": ballchasing_id})
        return games[0] if games else None

class PlayerStatsRepository(BaseRepository[PlayerStats]):
    def __init__(self):
        super().__init__(PlayerStats, "player_stats")
    
    async def find_by_player_and_game(self, player_id: str, game_id: str) -> PlayerStats:
        stats = await self.find({
            "player": ObjectId(player_id),
            "game": ObjectId(game_id)
        })
        return stats[0] if stats else None
    
    async def find_by_player(self, player_id: str) -> list[PlayerStats]:
        return await self.find({"player": ObjectId(player_id)})

class TournamentRepository(BaseRepository[Tournament]):
    def __init__(self):
        super().__init__(Tournament, "tournaments")

class BallchasingSyncRepository(BaseRepository[BallchasingSync]):
    def __init__(self):
        super().__init__(BallchasingSync, "ballchasing_sync")
    
    async def get_latest_by_type(self, sync_type: str) -> BallchasingSync:
        cursor = self.collection.find({"sync_type": sync_type}).sort("last_sync", -1).limit(1)
        async for doc in cursor:
            return BallchasingSync(**doc)
        return None