# File: ballchasing_service.py
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from bson import ObjectId

from models import Player, Match, Game, PlayerStats, BallchasingSync
from models.repositories import (
    PlayerRepository, TeamRepository, MatchRepository, 
    GameRepository, PlayerStatsRepository, BallchasingSyncRepository
)

class BallchasingService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://ballchasing.com/api"
        self.headers = {"Authorization": f"{api_key}"}
        
        self.player_repo = PlayerRepository()
        self.team_repo = TeamRepository()
        self.match_repo = MatchRepository()
        self.game_repo = GameRepository()
        self.player_stats_repo = PlayerStatsRepository()
        self.sync_repo = BallchasingSyncRepository()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the ballchasing API"""
        url = f"{self.base_url}/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise Exception(f"API request failed with status {response.status}: {text}")
    
    async def sync_replay(self, replay_id: str) -> Game:
        """Sync a replay from ballchasing API"""
        # Record sync start
        sync = BallchasingSync(
            sync_type="replay",
            status="in_progress",
            details=f"Syncing replay {replay_id}"
        )
        await self.sync_repo.create(sync)
        
        try:
            # Get replay data
            replay_data = await self._make_request(f"replays/{replay_id}")
            
            # Process players
            blue_player_ids = []
            orange_player_ids = []
            
            for team_color, team_data in replay_data["blue"].items():
                for player_data in team_data["players"]:
                    # Find or create player
                    player = await self._process_player(player_data)
                    
                    if team_color == "blue":
                        blue_player_ids.append(player.id)
                    else:
                        orange_player_ids.append(player.id)
                    
                    # Create player stats
                    await self._process_player_stats(player, replay_id, team_color, player_data)
            
            # Create game
            game = Game(
                ballchasing_id=replay_id,
                match=None,  # This would need to be set later when matches are created
                map=replay_data["map_name"],
                duration=replay_data["duration"],
                blue_players=blue_player_ids,
                orange_players=orange_player_ids,
                score_blue=replay_data["blue"]["score"],
                score_orange=replay_data["orange"]["score"],
                winner="blue" if replay_data["blue"]["score"] > replay_data["orange"]["score"] else "orange",
                stats={
                    "blue": {
                        "goals": replay_data["blue"]["goals"],
                        "shots": replay_data["blue"]["shots"],
                        "saves": replay_data["blue"]["saves"],
                        "assists": replay_data["blue"]["assists"]
                    },
                    "orange": {
                        "goals": replay_data["orange"]["goals"],
                        "shots": replay_data["orange"]["shots"],
                        "saves": replay_data["orange"]["saves"],
                        "assists": replay_data["orange"]["assists"]
                    }
                },
                replay_url=f"https://ballchasing.com/replay/{replay_id}"
            )
            game = await self.game_repo.create(game)
            
            # Update sync record
            sync.status = "success"
            sync.details = f"Successfully synced replay {replay_id}"
            await self.sync_repo.update(str(sync.id), sync.dict())
            
            return game
            
        except Exception as e:
            # Update sync record with error
            sync.status = "failed"
            sync.details = f"Failed to sync replay {replay_id}: {str(e)}"
            await self.sync_repo.update(str(sync.id), sync.dict())
            raise
    
    async def _process_player(self, player_data: Dict[str, Any]) -> Player:
        """Find or create a player from ballchasing data"""
        # Check if player exists
        player = await self.player_repo.find_by_platform_id(
            player_data["platform"], 
            player_data["id"]
        )
        
        if not player:
            # Create new player
            player = Player(
                ballchasing_id=player_data.get("ballchasing_id"),
                name=player_data["name"],
                platform=player_data["platform"],
                platform_id=player_data["id"],
                mmr={}  # MMR would be updated separately
            )
            player = await self.player_repo.create(player)
        
        return player
    
    async def _process_player_stats(
        self, 
        player: Player, 
        game_id: str, 
        team: str, 
        stats_data: Dict[str, Any]
    ) -> PlayerStats:
        """Create player stats for a game"""
        game = await self.game_repo.find_by_ballchasing_id(game_id)
        
        if not game:
            raise ValueError(f"Game with ballchasing_id {game_id} not found")
        
        # Create player stats
        player_stats = PlayerStats(
            player=player.id,
            game=game.id,
            team=team,
            goals=stats_data.get("goals", 0),
            assists=stats_data.get("assists", 0),
            saves=stats_data.get("saves", 0),
            shots=stats_data.get("shots", 0),
            score=stats_data.get("score", 0),
            mvp=stats_data.get("mvp", False),
            boost={
                "bpm": stats_data.get("boost", {}).get("bpm", 0),
                "avg": stats_data.get("boost", {}).get("avg", 0),
                "stolen": stats_data.get("boost", {}).get("stolen", 0)
            },
            movement={
                "avg_speed": stats_data.get("movement", {}).get("avg_speed", 0),
                "total_distance": stats_data.get("movement", {}).get("total_distance", 0),
                "time_supersonic": stats_data.get("movement", {}).get("time_supersonic", 0),
                "time_ground": stats_data.get("movement", {}).get("time_ground", 0),
                "time_air": stats_data.get("movement", {}).get("time_air", 0)
            },
            positioning={
                "time_defensive_half": stats_data.get("positioning", {}).get("time_defensive_half", 0),
                "time_offensive_half": stats_data.get("positioning", {}).get("time_offensive_half", 0),
                "time_behind_ball": stats_data.get("positioning", {}).get("time_behind_ball", 0),
                "time_infront_ball": stats_data.get("positioning", {}).get("time_infront_ball", 0)
            }
        )
        
        return await self.player_stats_repo.create(player_stats)