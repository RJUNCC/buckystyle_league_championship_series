# models/team.py
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rl_league")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

class Team:
    collection = db.teams

    @classmethod
    async def update_standings(cls, team_name: str, won: bool):
        update = {
            "$inc": {
                "wins" if won else "losses": 1,
                "series_played": 1
            }
        }
        await cls.collection.update_one({"name": team_name}, update)

    @classmethod
    async def get_standings(cls):
        pipeline = [
            {"$project": {
                "name": 1,
                "wins": {"$ifNull": ["$wins", 0]},
                "losses": {"$ifNull": ["$losses", 0]},
                "series_played": {"$ifNull": ["$series_played", 0]}
            }},
            {"$sort": {"wins": -1, "series_played": 1}}
        ]
        return await cls.collection.aggregate(pipeline).to_list(None)

    @classmethod
    async def create_team(cls, name: str, captain_id: int):
        await cls.collection.insert_one({
            "name": name,
            "captain_id": captain_id,
            "players": [captain_id],
            "created_at": datetime.utcnow()
        })

    @classmethod
    async def add_player(cls, team_name: str, player_id: int):
        await cls.collection.update_one(
            {"name": team_name},
            {"$addToSet": {"players": player_id}}
        )

    @classmethod
    async def get_all_teams(cls):
        return await cls.collection.find().to_list(None)

    @classmethod
    async def get_team_by_player(cls, player_id: int):
        return await cls.collection.find_one({"players": player_id})


    @classmethod
    async def get_team_by_name(cls, name: str):
        return await cls.collection.find_one({"name": name})
    
    @classmethod
    async def update_team_stats(cls, team_name: str, goals_for: int, goals_against: int):
        update = {
            "$inc": {
                "stats.goals_for": goals_for,
                "stats.goals_against": goals_against,
                "stats.goal_difference": goals_for - goals_against,
                "stats.games_played": 1
            }
        }
        await cls.collection.update_one({"name": team_name}, update)

    @classmethod
    async def get_team_stats(cls, team_name: str):
        return await cls.collection.find_one(
            {"name": team_name},
            {"stats": 1, "_id": 0}
        )

    @classmethod
    async def reset_all_standings(cls):
        await cls.collection.update_many(
            {},
            {"$set": {"wins": 0, "losses": 0, "series_played": 0}}
        )

    @classmethod
    async def get_top_teams(cls, limit):
        return await cls.collection.find().sort("wins", -1).limit(limit).to_list(None)