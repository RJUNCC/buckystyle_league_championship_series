# bot.py
import discord
import os
import signal
import sys
from dotenv import load_dotenv
from cogs.availability import AvailabilityCog
from cogs.ballchasing import BallchasingCog
from cogs.admin import AdminCog
from models.player import client

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
            self.add_cog(BallchasingCog(self))
            self.add_cog(AdminCog(self))
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
        bot.run(os.getenv("DISCORD_TOKEN"))
    except KeyboardInterrupt:
        handle_exit()
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        sys.exit(1)
