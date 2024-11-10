# discord_bot/cogs/commands_cog.py
import os
import discord
from discord.ext import commands, tasks
from discord import Intents
from typing import Final
from dotenv import load_dotenv
from responses import get_response
import asyncio
import pandas as pd
from discord_bot.utils.database import get_team_stats, get_player_stats
from discord_bot.utils.visualization import create_radar_chart, create_kpi_panel, create_team_table_image
from config.config import Config
import io

class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.TIMEOUT_DURATION = 60  # Timeout duration in seconds
        self.channels = [
            (Config.CHANNEL_ID1, "# **Updated team stats**", "images/table2.png"),
            (Config.CHANNEL_ID2, "# **Updated player data**", "images/player_data.png"),
        ]
        self.check_data_changes.start()

    def cog_unload(self):
        self.check_data_changes.cancel()

    @tasks.loop(seconds=86400)  # Run once every 24 hours
    async def check_data_changes(self):
        """
        Periodically check for data changes and update Discord channels accordingly.
        """
        try:
            # Load and compare dataframes
            final_df = pd.read_parquet("data/parquet/final.parquet")
            final_player_df = pd.read_parquet("data/parquet/final_player_data.parquet")

            # Check if temp files exist
            final_temp_path = "data/parquet/final_temp.parquet"
            final_player_temp_path = "data/parquet/final_player_data_temp.parquet"
            main_data_changed = player_data_changed = False

            if not os.path.exists(final_temp_path):
                main_data_changed = True
                print(f"{final_temp_path} does not exist. Will create it.")

            if not os.path.exists(final_player_temp_path):
                player_data_changed = True
                print(f"{final_player_temp_path} does not exist. Will create it.")

            # Check for changes if temp files exist
            if not main_data_changed:
                final_temp_df = pd.read_parquet(final_temp_path)
                main_data_changed = not final_df.equals(final_temp_df)

            if not player_data_changed:
                final_player_temp_df = pd.read_parquet(final_player_temp_path)
                player_data_changed = not final_player_df.equals(final_player_temp_df)

            # Exit early if no changes detected
            if not main_data_changed and not player_data_changed:
                print("No changes detected. Exiting without updating channels.")
                return

            # Update temp files for data that changed or if they didn't exist
            if main_data_changed:
                final_df.to_parquet(final_temp_path)
                print(f"Updated {final_temp_path}")

            if player_data_changed:
                final_player_df.to_parquet(final_player_temp_path)
                print(f"Updated {final_player_temp_path}")

            # Iterate over each channel and send messages
            for channel_id, message, image_path in self.channels:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self.remove_previous_image_message(channel)
                    await channel.send(message)
                    await self.send_new_image(channel, image_path)

        except Exception as e:
            print(f"Error in check_data_changes: {e}")

    @check_data_changes.before_loop
    async def before_check_data_changes(self):
        await self.bot.wait_until_ready()

    @commands.command(name='draft_odds')
    async def draft_odds(self, ctx):
        """
        Send draft odds for the next season.
        """
        teams_df = get_team_stats()
        sorted_teams = teams_df.sort_values('EPI Score').reset_index(drop=True)
        sorted_teams['Draft_Odds (%)'] = (sorted_teams.index + 1) * 2  # Simplified example

        draft_odds_table = sorted_teams[['Team', 'Draft_Odds (%)']].to_markdown(index=False)
        await ctx.send(f"**Draft Odds for Next Season:**\n```{draft_odds_table}```")

    @commands.command(name='predict')
    async def predict(self, ctx, player_name: str):
        """
        Provide predictions for a specific player.
        """
        players_df = get_player_stats()
        player = players_df[players_df['Player'].str.lower() == player_name.lower()]
        if player.empty:
            await ctx.send(f"Player '{player_name}' not found.")
            return

        player = player.iloc[0]
        radar_img = create_radar_chart(player)
        kpi_img = create_kpi_panel(player)

        files = [
            discord.File(io.BytesIO(radar_img), filename=f"{player['Player']}_radar.png"),
            discord.File(kpi_img, filename=f"{player['Player']}_kpi.png")
        ]

        await ctx.send(
            content=f"**Prediction for {player['Player']}**",
            files=files
        )

    async def remove_previous_image_message(self, channel):
        """
        Remove the previous image message from the channel.
        """
        async for message in channel.history(limit=100):
            if message.author == self.bot.user:
                try:
                    await message.delete()
                    print("Previous message deleted.")
                    return  # Stop further deletions
                except Exception as e:
                    print(f"Failed to delete the message: {e}")
        print("No previous message found to delete.")

    async def send_new_image(self, channel, file_path):
        """
        Send a new image to the specified channel.
        """
        if not os.path.exists(file_path):
            print(f"Image file {file_path} does not exist.")
            return

        with open(file_path, 'rb') as f:
            await channel.send(file=discord.File(f))
            print("New image sent.")

def setup(bot):
    bot.add_cog(CommandsCog(bot))
