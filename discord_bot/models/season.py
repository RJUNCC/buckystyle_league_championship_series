# discord_bot/models/season.py
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rl_league")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

class Season:
    collection = db.seasons

    @classmethod
    async def create_season(cls, number: int, start_date: datetime, ballchasing_group_id: str):
        await cls.collection.insert_one({
            "number": number,
            "start_date": start_date,
            "end_date": None,
            "ballchasing_group_id": ballchasing_group_id,
            "is_active": True
        })

    @classmethod
    async def end_current_season(cls):
        current_season = await cls.get_current_season()
        if current_season:
            await cls.collection.update_one(
                {"_id": current_season["_id"]},
                {"$set": {"end_date": datetime.utcnow(), "is_active": False}}
            )

    @classmethod
    async def get_current_season(cls):
        return await cls.collection.find_one({"is_active": True})

    @classmethod
    async def get_all_seasons(cls):
        return await cls.collection.find().sort("number", -1).to_list(None)
    
    @classmethod
    async def get_season(cls, season_number):
        return await cls.collection.find_one({"number": season_number})

    # discord_bot/models/team.py
    # Add this method to the Team class
    @classmethod
    async def get_all_teams_stats(cls, season_number):
        return await cls.collection.find({"season": season_number}).sort("wins", -1).to_list(None)
