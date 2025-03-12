# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "discord",
#     "logging",
#     "pathlib",
#     "python-dotenv",
# ]
# ///
# discord_bot/cogs/send_images.py
import os
import discord
from discord import File
from pathlib import Path
import logging
from discord.ext import commands

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config

class ImageSenderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        
        # Validate environment variables
        if not all([self.config._discord_token, self.config._player_channel_id, self.config._team_channel_id]):
            self.logger.error("Missing required environment variables")
            raise RuntimeError("Missing environment variables")

        # Define image paths
        self.image_paths = {
            "player": [f"images/{self.config.all_player_data}.png"],
            "team": [f"images/{self.config.all_team_data}.png"],
            "playoff": [
                f"images/{self.config.playoff_player_path}.png",
                f"images/{self.config.playoff_team_path}.png"
            ]
        }

    async def remove_previous_messages(self, channel):
        """Remove all messages sent by the bot in the specified channel."""
        try:
            deleted = await channel.purge(check=lambda m: m.author == self.bot.user)
            self.logger.info(f"Deleted {len(deleted)} messages in {channel.name}")
        except Exception as e:
            self.logger.error(f"Error purging messages: {str(e)}")

    async def send_images_to_channel(self, channel_id, image_paths):
        """Send images to a specific channel"""
        channel = self.bot.get_channel(channel_id)
        if not channel:
            self.logger.error(f"Channel {channel_id} not found")
            return

        await self.remove_previous_messages(channel)

        for path in image_paths:
            if not os.path.exists(path):
                self.logger.warning(f"Image not found: {path}")
                continue
            
            try:
                with open(path, "rb") as f:
                    await channel.send(file=File(f, filename=Path(path).name))
                    self.logger.info(f"Sent image to {channel.name}: {path}")
            except Exception as e:
                self.logger.error(f"Failed to send {path}: {str(e)}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Automatically send images when cog loads"""
        self.logger.info("Image sender cog ready")

    async def send_all_images(self):
        """Main method to trigger image sending"""
        try:
            # Player stats
            await self.send_images_to_channel(
                int(self.config._player_channel_id),
                self.image_paths["player"]
            )
            
            # Team stats
            await self.send_images_to_channel(
                int(self.config._team_channel_id),
                self.image_paths["team"]
            )
            
            # Playoff stats (optional)
            if self.config.playoff_player_path and self.config.playoff_team_path:
                await self.send_images_to_channel(
                    int(os.getenv('PLAYOFF_CHANNEL_ID')),
                    self.image_paths["playoff"]
                )
                
        except ValueError as e:
            self.logger.error(f"Invalid channel ID: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error sending images: {str(e)}")

def setup(bot):
    bot.add_cog(ImageSenderCog(bot))

