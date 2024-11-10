# discord_bot/cogs/data_updates.py
from discord.ext import commands, tasks
from discord import File
from utils.database import get_team_stats, get_player_stats
from utils.visualization import create_team_table_image, create_player_data_image
import pandas as pd
import io
import asyncio

class DataUpdates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_updates.start()

    def cog_unload(self):
        self.send_updates.cancel()

    @tasks.loop(hours=24)
    async def send_updates(self):
        channel1 = self.bot.get_channel(Config.CHANNEL_ID1)
        channel2 = self.bot.get_channel(Config.CHANNEL_ID2)

        if channel1:
            # Fetch and send team stats
            team_stats = get_team_stats()
            team_image = create_team_table_image(team_stats)
            file1 = File(io.BytesIO(team_image), filename="team_stats.png")

            await self.cleanup_previous_images(channel1)
            await channel1.send("# **Updated team stats**", file=file1)

        if channel2:
            # Fetch and send player data
            player_stats = get_player_stats()
            player_image = create_player_data_image(player_stats)
            file2 = File(io.BytesIO(player_image), filename="player_data.png")

            await self.cleanup_previous_images(channel2)
            await channel2.send("# **Updated player data**", file=file2)

    @send_updates.before_loop
    async def before_send_updates(self):
        await self.bot.wait_until_ready()

    async def cleanup_previous_images(self, channel):
        async for message in channel.history(limit=100):
            if message.author == self.bot.user:
                try:
                    await message.delete()
                    print(f"Deleted message {message.id} in channel {channel.id}")
                except Exception as e:
                    print(f"Failed to delete message {message.id}: {e}")

def setup(bot):
    bot.add_cog(DataUpdates(bot))
