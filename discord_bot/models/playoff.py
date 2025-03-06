# discord_bot/models/playoff.py
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "rl_league")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

class Playoff:
    collection = db.playoffs

    @classmethod
    async def create_bracket(cls, season_number, teams):
        bracket = {
            "season_number": season_number,
            "created_at": datetime.utcnow(),
            "rounds": [
                {
                    "round_number": 1,
                    "matches": [{"team1": teams[i], "team2": teams[-i-1], "winner": None} for i in range(len(teams)//2)]
                }
            ],
            "winner": None,
            "completed": False
        }
        await cls.collection.insert_one(bracket)

    @classmethod
    async def update_match(cls, season_number, round_number, match_index, winner):
        playoff = await cls.collection.find_one({"season_number": season_number, "completed": False})
        if not playoff:
            raise ValueError("No active playoff found for this season")

        # Update the match result
        playoff["rounds"][round_number-1]["matches"][match_index]["winner"] = winner

        # Check if the round is complete
        current_round = playoff["rounds"][round_number-1]
        if all(match["winner"] for match in current_round["matches"]):
            # Prepare next round if not final
            if round_number < len(playoff["rounds"]):
                winners = [match["winner"] for match in current_round["matches"]]
                next_round = {
                    "round_number": round_number + 1,
                    "matches": [{"team1": winners[i], "team2": winners[i+1], "winner": None} for i in range(0, len(winners), 2)]
                }
                playoff["rounds"].append(next_round)
            else:
                # Final round completed
                playoff["winner"] = winner
                playoff["completed"] = True

        await cls.collection.replace_one({"_id": playoff["_id"]}, playoff)

    @classmethod
    async def get_current_bracket(cls, season_number):
        return await cls.collection.find_one({"season_number": season_number, "completed": False})

    @classmethod
    async def get_playoff_winner(cls, season_number):
        playoff = await cls.collection.find_one({"season_number": season_number, "completed": True})
        return playoff["winner"] if playoff else None
