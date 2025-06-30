# File: discord_bot/bot.py (FINAL VERSION)

import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your cogs
from cogs.draft_prob import DraftLotteryCog
from cogs.player_profiles import PlayerProfilesCog
from cogs.profile_linking import ProfileLinkingCog
from cogs.blcsx_profiles import BLCSXProfilesCog

# Import database setup
# from models.scheduling import initialize_database
from models.player_profile import Base, engine

class RocketLeagueBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Important for profile features
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='Rocket League Discord Bot with Player Profiles'
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
        cogs = [
            DraftLotteryCog,        # Your existing
            PlayerProfilesCog,      # Your existing  
            ProfileLinkingCog,      # Your existing
            BLCSXProfilesCog        # NEW: Advanced BLCSX system
        ]
        
        for cog in cogs:
            try:
                self.add_cog(cog(self))
                print(f"✅ {cog.__name__} loaded successfully")
            except Exception as e:
                print(f"❌ Error loading {cog.__name__}: {str(e)}")

# Initialize bot instance
bot = RocketLeagueBot()

async def main():
    """Main async function to run the bot"""
    
    # Check for required environment variables
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        print("❌ DISCORD_TOKEN not found in environment variables!")
        print("Please add your Discord bot token to the .env file")
        return
    
    # # Initialize databases
    # try:
    #     initialize_database()  # Your existing scheduling database
    #     Base.metadata.create_all(engine)  # Player profiles database
    #     print("✅ Databases initialized successfully")
    # except Exception as e:
    #     print(f"❌ Database initialization failed: {e}")
    #     return
    
    # Load cogs
    bot.load_cogs()
    
    # Optional: Start ballchasing.com monitoring
    try:
        from services.ballchasing_service import start_monitoring_group
        group_id = os.getenv('BALLCHASING_GROUP_ID')
        api_key = os.getenv('BALLCHASING_API_KEY')
        
        if group_id and api_key:
            start_monitoring_group(group_id)
            print(f"✅ Started monitoring ballchasing group: {group_id}")
        else:
            print("⚠️ Ballchasing monitoring disabled (missing GROUP_ID or API_KEY)")
    except Exception as e:
        print(f"⚠️ Ballchasing monitoring not started: {e}")
    
    # Start the bot
    async with bot:
        try:
            print("🚀 Starting bot...")
            await bot.start(discord_token)
        except discord.LoginFailure:
            print("❌ Invalid Discord token! Please check your .env file")
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")

if __name__ == "__main__":
    print("🎮 Rocket League Discord Bot Starting...")
    print("=" * 50)
    asyncio.run(main())