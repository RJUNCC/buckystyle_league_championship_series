# discord_bot/cogs/predictions.py
import discord
from discord.ext import commands
from utils.database import get_player_stats
from utils.visualization import create_radar_chart, create_kpi_panel
import pandas as pd
import io

class Predictions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='predict')
    async def predict(self, ctx, player_name: str):
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

def setup(bot):
    bot.add_cog(Predictions(bot))
