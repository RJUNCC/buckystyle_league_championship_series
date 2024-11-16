# cogs/data_updates.py
from discord.ext import commands, tasks
from discord import File
from config.config import Config
from pathlib import Path
import pandas as pd
import dataframe_image as dfi
import io
import logging

class DataUpdates(commands.Cog):
    def __init__(self, bot, config: Config):
        self.bot = bot
        self.config = config
        self.send_updates.start()

    def cog_unload(self):
        self.send_updates.cancel()

    @tasks.loop(hours=24)
    async def send_updates(self):
        channel1 = self.bot.get_channel(self.config.channel_id1)
        channel2 = self.bot.get_channel(self.config.channel_id2)

        if channel1:
            # Assuming '../images/table2.png' is your updated team stats image
            team_image_path = Path("../images/table2.png")
            if team_image_path.exists():
                await self.cleanup_previous_images(channel1)
                await channel1.send("# **Updated team stats**", file=File(str(team_image_path)))
                logging.info(f"Sent updated team stats to channel {self.config.channel_id1}")
            else:
                logging.warning(f"Team image {team_image_path} does not exist.")

        if channel2:
            # Assuming '../images/player_data.png' is your updated player data image
            player_image_path = Path("../images/player_data.png")
            if player_image_path.exists():
                await self.cleanup_previous_images(channel2)
                await channel2.send("# **Updated player data**", file=File(str(player_image_path)))
                logging.info(f"Sent updated player data to channel {self.config.channel_id2}")
            else:
                logging.warning(f"Player image {player_image_path} does not exist.")

    @send_updates.before_loop
    async def before_send_updates(self):
        await self.bot.wait_until_ready()
        logging.info("DataUpdates task started.")

    async def cleanup_previous_images(self, channel):
        async for message in channel.history(limit=100):
            if message.author == self.bot.user:
                try:
                    await message.delete()
                    logging.info(f"Deleted message {message.id} in channel {channel.id}")
                except Exception as e:
                    logging.error(f"Failed to delete message {message.id}: {e}")
