# bot.py
import discord
import os
import signal
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from cogs.availability import AvailabilityCog
# from cogs.ballchasing import BallchasingCog
from cogs.admin import AdminCog
from cogs.team_management import TeamManagementCog
from cogs.series_management import SeriesManagementCog
from cogs.statistics import StatisticsCog
from cogs.scheduling import SchedulingCog
from cogs.season_management import SeasonManagementCog
from cogs.playoff_management import PlayoffManagementCog
from cogs.season_summary import SeasonSummaryCog
from models.player import client, initialize_db
import asyncio

load_dotenv()

class MyBot(discord.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        
        # Load cogs during initialization
        self.load_cogs()

    def load_cogs(self):
        """Load all cogs with error handling"""
        try:
            self.add_cog(AvailabilityCog(self))
            # self.add_cog(BallchasingCog(self))
            self.add_cog(AdminCog(self))
            self.add_cog(TeamManagementCog(self))
            self.add_cog(SeriesManagementCog(self))
            self.add_cog(StatisticsCog(self))
            self.add_cog(SchedulingCog(self))
            self.add_cog(SeasonManagementCog(self))
            self.add_cog(PlayoffManagementCog(self))
            self.add_cog(SeasonSummaryCog(self))
            print("✅ Cogs loaded successfully")
        except Exception as e:
            print(f"❌ Error loading cogs: {str(e)}")
            sys.exit(1)

    async def on_connect(self):
        """Handle database connection on startup"""
        print("\n🔗 Connecting to services...")
        try:
            await client.admin.command('ping')
            print("🟢 MongoDB connection successful")
        except Exception as e:
            print(f"🔴 MongoDB error: {str(e)}")
            sys.exit(1)

    async def on_disconnect(self):
        """Cleanup on shutdown"""
        print("\n🔌 Disconnecting...")
        client.close()

def handle_exit(signum, frame):
    """Graceful shutdown handler"""
    print("\n🛑 Received shutdown signal")
    client.close()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Initialize bot
    bot = MyBot()

    @bot.event
    async def on_ready():
        """Post-initialization setup"""
        print(f"\n🤖 Logged in as {bot.user} (ID: {bot.user.id})")
        print("🔁 Syncing commands globally...")
        await bot.sync_commands()
        print("✅ Bot ready")

    try:
        print("\n🚀 Starting bot...")
        asyncio.get_event_loop().run_until_complete(initialize_db())
        bot.run(os.getenv("DISCORD_TOKEN"))
    except KeyboardInterrupt:
        handle_exit()
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        sys.exit(1)
