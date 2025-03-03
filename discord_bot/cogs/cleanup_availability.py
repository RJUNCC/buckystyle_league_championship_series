import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def clear_all_availability():
    """Permanently remove all availability data"""
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    db = client.rl_league
    result = await db.players.update_many(
        {},
        {"$unset": {"availability": ""}}
    )
    print(f"✅ Cleared availability for {result.modified_count} players")

if __name__ == "__main__":
    import asyncio
    asyncio.run(clear_all_availability())
