# bot.py
import discord
import os
import sys
import asyncio
from aiohttp import web
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
# from cogs.availability import AvailabilityCog
# from cogs.admin import AdminCog
# from cogs.team_management import TeamManagementCog
# from cogs.series_management import SeriesManagementCog
# # from cogs.statistics import StatisticsCog
# from cogs.season_management import SeasonManagementCog
# from cogs.playoff_management import PlayoffManagementCog
# from cogs.season_summary import SeasonSummaryCog
from cogs.draft_prob import DraftLotteryCog 
from cogs.scheduling import EnhancedSchedulingCog
# from models.player import initialize_db
from loguru import logger

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
        cogs = [ DraftLotteryCog, EnhancedSchedulingCog  # This handles both features
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
        
        # Start health check server after bot is ready
        await self.start_health_server()
        print("✅ Bot ready")

    async def start_health_server(self):
        """Start health check server for DigitalOcean"""
        async def health_check(request):
            return web.Response(text="BLCS Bot is running!", status=200)

        app = web.Application()
        app.router.add_get('/health', health_check)
        app.router.add_get('/', health_check)  # For root path too
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Use PORT environment variable or default to 8080
        port = int(os.getenv('PORT', 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"🌐 Health check server running on port {port}")

bot = MyBot()

async def main():
    """Main async function to run the bot"""
    # Initialize player database
    # try:
    #     initialize_db()
    #     print("✅ Player database initialized")
    # except Exception as e:
    #     print(f"❌ Player database initialization error: {e}")
    
    # Initialize scheduling database
    try:
        from models.scheduling import Base, engine
        Base.metadata.create_all(engine)
        print("✅ Scheduling database initialized")
        
        # Optional: Clean up old sessions on startup
        from models.scheduling import cleanup_old_sessions
        cleaned = cleanup_old_sessions(days_old=30)
        if cleaned > 0:
            print(f"🧹 Cleaned up {cleaned} old scheduling sessions")
    except Exception as e:
        print(f"⚠️ Scheduling database initialization error (non-fatal): {e}")
    
    # Start the bot
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    logger.info("\n🚀 Starting bot...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")