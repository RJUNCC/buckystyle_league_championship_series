# File: discord_bot/bot.py (FINAL POSTGRESQL VERSION WITH BLCSX STATS)

import discord
from discord.ext import commands
import asyncio
import os
import logging
from dotenv import load_dotenv
from aiohttp import web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import database configuration (FIRST - before other imports)
from models.database_config import initialize_database, get_engine

# Check for BLCSX stats dependencies
BLCSX_STATS_AVAILABLE = False
try:
    # These are the optional dependencies for blcsx_stats.py
    import numpy
    import pandas
    import sqlalchemy
    BLCSX_STATS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ BLCSX Stats dependencies not found, features will be disabled: {e}")


# Import the specific cogs you want to load
from cogs.draft_prob import DraftLotteryCog
from cogs.blcsx_stats import BLCSXStatsCog

# Import ballchasing integration
from services.ballchasing_stats_updater import initialize_ballchasing_updater

class RocketLeagueBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Important for profile features
        
        super().__init__(
            intents=intents,
            description='Rocket League Discord Bot with PostgreSQL & BLCSX Integration'
        )
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'✅ {self.user} has connected to Discord!')
        logger.info(f'📊 Connected to {len(self.guilds)} servers')
        
        # Note: py-cord automatically syncs slash commands, no manual sync needed
        logger.info('✅ Slash commands auto-synced by py-cord')
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new server"""
        logger.info(f'🆕 Joined new server: {guild.name} (ID: {guild.id})')
        # py-cord handles command syncing automatically for new guilds
    
    def load_cogs(self):
        """Load a specific list of cogs."""
        cogs_to_load = [
            DraftLotteryCog,
        ]

        # Conditionally add BLCSXStatsCog if its dependencies are met
        if BLCSX_STATS_AVAILABLE:
            cogs_to_load.append(BLCSXStatsCog)
        else:
            logger.warning("⚠️ BLCSXStatsCog not loaded due to missing dependencies.")

        for cog in cogs_to_load:
            try:
                self.add_cog(cog(self))
                logger.info(f"✅ Loaded cog: {cog.__name__}")
            except Exception as e:
                logger.error(f"❌ Failed to load cog {cog.__name__}: {e}")

# Initialize bot instance
bot = RocketLeagueBot()

async def health_check_server():
    """Health check server for DigitalOcean"""
    async def health(request):
        """Basic health check"""
        return web.Response(text="OK", status=200)
    
    async def bot_status(request):
        """Detailed bot and database status"""
        try:
            # Test database connection
            engine = get_engine()
            db_status = "healthy"
            db_type = "unknown"
            
            if engine:
                try:
                    with engine.connect() as conn:
                        from sqlalchemy import text
                        conn.execute(text("SELECT 1"))
                    
                    db_url = str(engine.url)
                    db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
                except:
                    db_status = "unhealthy"
            
            status = {
                "status": "healthy",
                "bot_ready": bot.is_ready(),
                "guilds": len(bot.guilds) if bot.is_ready() else 0,
                "users": len(bot.users) if bot.is_ready() else 0,
                "database_status": db_status,
                "database_type": db_type,
                "blcsx_stats_enabled": BLCSX_STATS_AVAILABLE and os.getenv('BALLCHASING_API_KEY') is not None
            }
            return web.json_response(status)
            
        except Exception as e:
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=500)
    
    # Create web application
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.router.add_get("/status", bot_status)
    
    # Setup and start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Health check server started on port {port}")

async def main():
    """Main async function to run the bot"""
    
    # Check for required environment variables
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        logger.error("❌ DISCORD_TOKEN not found in environment variables!")
        logger.error("Please add your Discord bot token to the .env file")
        return
    
    # Start health check server for DigitalOcean
    try:
        asyncio.create_task(health_check_server())
        logger.info("🏥 Health check server task created")
    except Exception as e:
        logger.warning(f"⚠️ Health check server failed to start: {e}")
    
    # Initialize PostgreSQL database
    try:
        logger.info("🔄 Initializing database connection...")
        initialize_database()
        try:
            logger.info("🔧 Checking for database migrations...")
            from sqlalchemy import text
            engine = get_engine()
            with engine.connect() as conn:
                # Check if ballchasing_platform column exists
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'player_profiles' 
                    AND column_name = 'ballchasing_platform'
                """)
                result = conn.execute(check_query)
                if not result.fetchone():
                    # Add missing column
                    logger.info("🔄 Adding missing ballchasing_platform column...")
                    conn.execute(text("ALTER TABLE player_profiles ADD COLUMN ballchasing_platform VARCHAR(50)"))
                    conn.commit()
                    logger.info("✅ Database migration completed successfully")
                else:
                    logger.info("✅ Database schema is up to date")
        except Exception as e:
            logger.warning(f"⚠️ Database migration check failed: {e}")
        logger.info("✅ PostgreSQL database initialized successfully")
        
        # Log database info
        engine = get_engine()
        if engine:
            db_url = str(engine.url)
            if "postgresql" in db_url:
                # Extract host info for logging (without credentials)
                try:
                    host_part = db_url.split('@')[1].split('/')[0]
                    logger.info(f"📊 Connected to PostgreSQL: {host_part}")
                except:
                    logger.info("📊 Connected to PostgreSQL database")
            else:
                logger.info("📊 Using SQLite for local development")
                
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        logger.error("Bot cannot start without database connection")
        return
    
    # Initialize BLCSX ballchasing integration
    try:
        ballchasing_api_key = os.getenv('BALLCHASING_API_KEY')
        if ballchasing_api_key and BLCSX_STATS_AVAILABLE:
            logger.info("✅ BLCSX ballchasing integration initialized")
            logger.info("   🎮 BLCSX Stats commands available:")
            logger.info("   /blcs_profile - Comprehensive player profiles")
            logger.info("   /blcs_leaderboard - Dominance quotient rankings")
            logger.info("   /blcs_link - Link ballchasing.com account")
            logger.info("   /blcs_update - Update stats (admin only)")
        elif not BLCSX_STATS_AVAILABLE:
            logger.warning("⚠️ BLCSX stats unavailable - missing dependencies (psycopg2, pandas, numpy)")
            logger.warning("   Install with: pip install psycopg2-binary pandas numpy aiohttp")
        else:
            logger.warning("⚠️ BALLCHASING_API_KEY not found - BLCSX stats features disabled")
            logger.warning("   Add BALLCHASING_API_KEY to .env file to enable comprehensive stats")
    except Exception as e:
        logger.error(f"⚠️ BLCSX integration failed to initialize: {e}")
    
    # Initialize traditional ballchasing integration (if exists)
    try:
        if os.path.exists('services/ballchasing_stats_updater.py'):
            ballchasing_updater = initialize_ballchasing_updater(os.getenv('BALLCHASING_API_KEY', ''))
            logger.info("✅ Traditional ballchasing integration initialized")
    except Exception as e:
        logger.warning(f"⚠️ Traditional ballchasing integration failed: {e}")
    
    # Load cogs
    bot.load_cogs()
    
    # Start the bot
    async with bot:
        try:
            logger.info("🚀 Starting Discord bot...")
            await bot.start(discord_token)
        except discord.LoginFailure:
            logger.error("❌ Invalid Discord token! Please check your .env file")
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    print("🎮 Rocket League Discord Bot")
    print("💾 PostgreSQL Database Integration")
    print("🏆 BLCSX Comprehensive Stats Integration")
    print("📊 Advanced Player Analytics & Rankings")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"\n💥 Bot crashed: {e}")
        raise