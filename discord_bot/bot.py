# File: discord_bot/bot.py

import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from aiohttp import web

# Load environment variables
load_dotenv()

# Import your cogs
from cogs.draft_prob import DraftLotteryCog
from cogs.player_profiles import PlayerProfilesCog
from cogs.profile_linking import ProfileLinkingCog
from cogs.blcsx_profiles import BLCSXProfilesCog
from cogs.enhanced_profiles import EnhancedProfilesCog
from cogs.blcs_stats import BLCSStatsCog  

# Import database setup
# from models.scheduling import initialize_database
from models.player_profile import Base, engine

# Import ballchasing integration
from services.ballchasing_stats_updater import initialize_ballchasing_updater

class RocketLeagueBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Important for profile features
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='Rocket League Discord Bot with BLCS Integration'
        )
    
    async def on_ready(self):
        """Called when bot is ready"""
        print(f'✅ {self.user} has connected to Discord!')
        print(f'📊 Connected to {len(self.guilds)} servers')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f'✅ Synced {len(synced)} command(s)')
        except Exception as e:
            print(f'❌ Failed to sync commands: {e}')
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new server"""
        print(f'🆕 Joined new server: {guild.name} (ID: {guild.id})')
        
        # Try to sync commands for the new server
        try:
            await self.tree.sync(guild=guild)
            print(f'✅ Synced commands for {guild.name}')
        except Exception as e:
            print(f'❌ Failed to sync commands for {guild.name}: {e}')
    
    def load_cogs(self):
        """Load all cogs with error handling"""
        cogs = [
            DraftLotteryCog,        # Draft lottery + scheduling
            PlayerProfilesCog,      # Basic player profiles
            ProfileLinkingCog,      # Ballchasing.com linking
            BLCSXProfilesCog,       # Advanced BLCSX profiles
            EnhancedProfilesCog,    # Creative themed profiles
            BLCSStatsCog            # NEW: BLCS stats integration
        ]
        
        for cog in cogs:
            try:
                self.add_cog(cog(self))
                print(f"✅ {cog.__name__} loaded successfully")
            except Exception as e:
                print(f"❌ Error loading {cog.__name__}: {str(e)}")

# Initialize bot instance
bot = RocketLeagueBot()

async def health_check_server():
    """Simple health check server for DigitalOcean"""
    async def health(request):
        """Health check endpoint"""
        return web.Response(text="OK", status=200)
    
    async def bot_status(request):
        """More detailed bot status"""
        status = {
            "status": "healthy",
            "bot_ready": bot.is_ready(),
            "guilds": len(bot.guilds) if bot.is_ready() else 0,
            "users": len(bot.users) if bot.is_ready() else 0
        }
        return web.json_response(status)
    
    # Create web application
    app = web.Application()
    app.router.add_get("/", health)          # Root path
    app.router.add_get("/health", health)    # Health check path
    app.router.add_get("/status", bot_status) # Detailed status
    
    # Setup and start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    # DigitalOcean expects port 8080 for health checks
    port = int(os.getenv('PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Health check server started on port {port}")

async def main():
    """Main async function to run the bot"""
    
    # Check for required environment variables
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        print("❌ DISCORD_TOKEN not found in environment variables!")
        print("Please add your Discord bot token to the .env file")
        return
    
    # Start health check server for DigitalOcean
    try:
        asyncio.create_task(health_check_server())
        print("🏥 Health check server task created")
    except Exception as e:
        print(f"⚠️ Health check server failed to start: {e}")
    
    # Initialize databases
    # try:
    #     initialize_database()  # Your existing scheduling database
    #     Base.metadata.create_all(engine)  # Player profiles database
    #     print("✅ Databases initialized successfully")
    # except Exception as e:
    #     print(f"❌ Database initialization failed: {e}")
    #     return
    
    # Initialize BLCS ballchasing integration
    try:
        ballchasing_api_key = os.getenv('BALLCHASING_API_KEY')
        if ballchasing_api_key:
            ballchasing_updater = initialize_ballchasing_updater(ballchasing_api_key)
            print("✅ BLCS ballchasing integration initialized")
            print("   Group: blcs-4-qz9e63f182")
            print("   🔗 Players can now use /link_blcs to connect their accounts")
        else:
            print("⚠️ BALLCHASING_API_KEY not found - BLCS features disabled")
            print("   Add BALLCHASING_API_KEY to .env file to enable BLCS stats")
    except Exception as e:
        print(f"⚠️ BLCS integration failed to initialize: {e}")
    
    # Load cogs
    bot.load_cogs()
    
    # Optional: Start general ballchasing.com monitoring (if you have other groups)
    try:
        from services.ballchasing_service import start_monitoring_group
        other_group_id = os.getenv('BALLCHASING_GROUP_ID')  # Different from BLCS group
        api_key = os.getenv('BALLCHASING_API_KEY')
        
        if other_group_id and api_key and other_group_id != "blcs-4-qz9e63f182":
            start_monitoring_group(other_group_id)
            print(f"✅ Started monitoring additional ballchasing group: {other_group_id}")
    except Exception as e:
        print(f"⚠️ Additional ballchasing monitoring not started: {e}")
    
    # Start the bot
    async with bot:
        try:
            print("🚀 Starting Discord bot...")
            await bot.start(discord_token)
        except discord.LoginFailure:
            print("❌ Invalid Discord token! Please check your .env file")
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    print("🎮 Rocket League Discord Bot with BLCS Integration")
    print("=" * 55)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n💥 Bot crashed: {e}")