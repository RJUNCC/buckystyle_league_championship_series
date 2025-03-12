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
import sys
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
        
        # Validate and convert channel IDs
        try:
            self.player_channel_id = int(self.config._player_channel_id)
            self.team_channel_id = int(self.config._team_channel_id)
            self.playoff_channel_id = int(os.getenv('PLAYOFF_CHANNEL_ID', 0)) or None
        except (ValueError, TypeError) as e:
            logging.error(f"Invalid channel ID format: {str(e)}")
            raise RuntimeError("Invalid channel IDs in configuration") from e

        # Absolute paths
        self.image_paths = {
            "player": [os.path.join("images", f"{self.config.all_player_data}.png")],
            "team": [os.path.join("images", f"{self.config.all_team_data}.png")]
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
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")
                
            # Verify files exist first
            valid_paths = []
            for path in image_paths:
                if os.path.exists(path):
                    valid_paths.append(path)
                else:
                    logging.warning(f"Missing image: {path}")
                    
            if not valid_paths:
                logging.error("No valid images to send")
                return
                
            await self.remove_previous_messages(channel)
            
            for path in valid_paths:
                with open(path, "rb") as f:
                    await channel.send(file=File(f, filename=Path(path).name))
                    
        except Exception as e:
            logging.error(f"Failed to send images: {str(e)}")
            raise


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

