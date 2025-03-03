from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, time, timedelta
import os
import pytz

# MongoDB Configuration
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://root:example@localhost:27017/rl_league?authSource=admin"
)

client = AsyncIOMotorClient(MONGO_URI)
db = client.rl_league

class Player:
    collection = db.players

    @classmethod
    async def update_availability(cls, player_id: int, dates: list, time_ranges: list):
        """Add multiple time ranges for selected dates"""
        updates = {}
        for date_str in dates:
            # Parse date from "Monday (Jul 15)" format
            date_part = date_str.split(" (")[1].strip(")")
            date_obj = datetime.strptime(f"{datetime.now().year} {date_part}", "%Y %b %d")
            
            # Store as ISO date string
            iso_date = date_obj.isoformat()
            
            # Convert time ranges to datetime objects
            time_entries = []
            for start_str, end_str in time_ranges:
                start = datetime.strptime(start_str, "%I:%M %p").time()
                end = datetime.strptime(end_str, "%I:%M %p").time()
                
                # Handle next-day times
                if end <= start:
                    end_date = date_obj + timedelta(days=1)
                else:
                    end_date = date_obj
                    
                time_entries.append({
                    "start": datetime.combine(date_obj, start),
                    "end": datetime.combine(end_date, end)
                })
            
            updates[f"availability.{iso_date}"] = {"$each": time_entries}
        
        await cls.collection.update_one(
            {"_id": player_id},
            {"$push": updates},
            upsert=True
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

async def initialize_db():
    """Initialize database indexes"""
    await Player.collection.create_index("last_updated")
