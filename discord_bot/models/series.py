# models/series.py
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rl_league")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

class Series:
    collection = db.series

    @classmethod
    async def create_series(cls, team1: str, team2: str, date: datetime, is_playoff: bool = False):
        return await cls.collection.insert_one({
            "team1": team1,
            "team2": team2,
            "date": date,
            "is_playoff": is_playoff,
            "games": [],
            "winner": None,
            "channel_id": None,
            "created_at": datetime.utcnow()
        })

    @classmethod
    async def update_channel_id(cls, series_id, channel_id):
        await cls.collection.update_one(
            {"_id": series_id},
            {"$set": {"channel_id": channel_id}}
        )

    @classmethod
    async def get_series(cls, series_id):
        return await cls.collection.find_one({"_id": series_id})

    @classmethod
    async def update_series(cls, series_id, game_result):
        series = await cls.get_series(series_id)
        series['games'].append(game_result)
        
        # Check for series winner
        team1_wins = sum(1 for game in series['games'] if game['winner'] == series['team1'])
        team2_wins = sum(1 for game in series['games'] if game['winner'] == series['team2'])
        
        wins_needed = 4 if series['is_playoff'] else 3
        if team1_wins == wins_needed:
            series['winner'] = series['team1']
        elif team2_wins == wins_needed:
            series['winner'] = series['team2']

        await cls.collection.update_one(
            {"_id": series_id},
            {"$set": {"games": series['games'], "winner": series['winner']}}
        )

    @classmethod
    async def get_upcoming_series(cls):
        return await cls.collection.find({"date": {"$gte": datetime.utcnow()}, "winner": None}).to_list(None)
    
    @classmethod
    async def report_game_result(cls, series_id, winner: str, score: dict):
        series = await cls.get_series(series_id)
        if not series:
            raise ValueError("Series not found")

        game_result = {
            "winner": winner,
            "score": score,
            "reported_at": datetime.utcnow()
        }
        series['games'].append(game_result)

        # Check for series winner
        wins_needed = 4 if series['is_playoff'] else 3
        team1_wins = sum(1 for game in series['games'] if game['winner'] == series['team1'])
        team2_wins = sum(1 for game in series['games'] if game['winner'] == series['team2'])

        if team1_wins == wins_needed:
            series['winner'] = series['team1']
        elif team2_wins == wins_needed:
            series['winner'] = series['team2']

        await cls.collection.update_one(
            {"_id": series_id},
            {"$set": {"games": series['games'], "winner": series['winner']}}
        )

        return series['winner']
    
    @classmethod
    async def get_series_by_channel(cls, channel_id: int):
        return await cls.collection.find_one({"channel_id": channel_id})
