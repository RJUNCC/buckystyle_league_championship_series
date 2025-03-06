from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, time
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rl_league")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

class Player:
    collection = db.players

    @classmethod
    async def set_availability(cls, player_id: int, availability: dict):
        """
        Set a player's availability
        availability: {
            "Monday": [{"start": "18:00", "end": "22:00"}],
            "Tuesday": [{"start": "19:00", "end": "23:00"}],
            ...
        }
        """
        await cls.collection.update_one(
            {"_id": player_id},
            {"$set": {"availability": availability}},
            upsert=True
        )

    @classmethod
    async def get_availability(cls, player_id: int):
        player = await cls.collection.find_one({"_id": player_id})
        return player.get("availability", {}) if player else {}

    @classmethod
    async def update_stats(cls, player_id: int, goals: int, assists: int, saves: int, shots: int):
        update = {
            "$inc": {
                "stats.goals": goals,
                "stats.assists": assists,
                "stats.saves": saves,
                "stats.shots": shots,
                "stats.games_played": 1
            }
        }
        await cls.collection.update_one({"_id": player_id}, update, upsert=True)

    @classmethod
    async def get_player_stats(cls, player_id: int):
        return await cls.collection.find_one(
            {"_id": player_id},
            {"stats": 1, "_id": 0}
        )

    @classmethod
    async def get_top_players(cls, stat: str, limit: int = 10):
        return await cls.collection.find(
            {"stats": {"$exists": True}},
            {"_id": 1, f"stats.{stat}": 1}
        ).sort(f"stats.{stat}", -1).limit(limit).to_list(None)

    @classmethod
    async def update_availability(cls, player_id: int, dates: list, start_time: str, end_time: str):
        availability = []
        for date_str in dates:
            date_obj = datetime.strptime(f"{datetime.now().year} {date_str}", "%Y %A (%b %d)")
            availability.append({
                "date": date_obj,
                "start": start_time,
                "end": end_time
            })
        
        await cls.collection.update_one(
            {"_id": player_id},
            {"$set": {"availability": availability}},
            upsert=True
        )

    @classmethod
    async def get_player_availability(cls, player_id: int):
        player = await cls.collection.find_one({"_id": player_id})
        return player.get("availability", []) if player else []

    @classmethod
    async def remove_past_availability(cls):
        now = datetime.now()
        await cls.collection.update_many(
            {},
            {"$pull": {"availability": {"date": {"$lt": now}}}}
        )



    @classmethod
    async def clear_all_availability(cls):
        """Admin: Complete availability reset"""
        result = await cls.collection.update_many(
            {},
            {"$unset": {"availability": ""}}
        )
        return f"Reset {result.modified_count} players' availability"

    @classmethod
    async def get_all_players(cls):
        """Get all players with cleaned data"""
        return await cls.collection.find().to_list(None)

    @classmethod
    async def remove_old_availability(cls):
        """Remove legacy string-formatted entries"""
        result = await cls.collection.update_many(
            {"availability": {"$type": "string"}},
            {"$unset": {"availability": ""}}
        )
        return f"Cleaned {result.modified_count} legacy entries"
    
    @classmethod
    async def clear_player_availability(cls, player_id: int):
        """Clear availability for a specific player"""
        await cls.collection.update_one(
            {"_id": player_id},
            {"$unset": {"availability": ""}}
        )

    @classmethod
    async def reset_all_stats(cls):
        await cls.collection.update_many(
            {},
            {"$set": {"stats": {}}}
        )

    @classmethod
    async def get_top_players(cls, season_number, limit=10):
        pipeline = [
            {"$match": {"season": season_number}},
            {"$project": {
                "name": 1,
                "top_stat_name": {"$arrayElemAt": [{"$objectToArray": "$stats"}, 0]},
                "top_stat_value": {"$max": {"$objectToArray": "$stats"}}
            }},
            {"$sort": {"top_stat_value": -1}},
            {"$limit": limit}
        ]
        return await cls.collection.aggregate(pipeline).to_list(None)

# Ensure the database connection is established
async def initialize_db():
    try:
        await client.admin.command('ping')
        print("Connected to MongoDB")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise
