# bot.py
import discord
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from cogs.availability import AvailabilityCog
from cogs.admin import AdminCog
from cogs.team_management import TeamManagementCog
from cogs.series_management import SeriesManagementCog
from cogs.statistics import StatisticsCog
from cogs.scheduling import SchedulingCog
from cogs.season_management import SeasonManagementCog
from cogs.playoff_management import PlayoffManagementCog
from cogs.season_summary import SeasonSummaryCog
# from cogs.send_images import ImageSenderCog
from models.player import initialize_db

load_dotenv()

class MyBot(discord.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        
        self.load_cogs()

    def load_cogs(self):
        """Load all cogs with error handling"""
        cogs = [
            AdminCog, AvailabilityCog, TeamManagementCog, SeriesManagementCog,
            StatisticsCog, SchedulingCog, SeasonManagementCog,
            PlayoffManagementCog, SeasonSummaryCog
        ]
        for cog in cogs:
            try:
                self.add_cog(cog(self))
                print(f"✅ {cog.__name__} loaded successfully")
            except Exception as e:
                print(f"❌ Error loading {cog.__name__}: {str(e)}")

    async def on_ready(self):
        print(f"\n🤖 Logged in as {self.user} (ID: {self.user.id})")
        print("🔁 Syncing commands globally...")
        await self.sync_commands()
        print("✅ Bot ready")

bot = MyBot()

if __name__ == "__main__":
    print("\n🚀 Starting bot...")
    bot.run(os.getenv("DISCORD_TOKEN"))
