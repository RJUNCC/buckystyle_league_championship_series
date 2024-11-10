# discord_bot/cogs/team_stats.py
from discord.ext import commands
from utils.database import get_team_stats
from utils.visualization import create_team_table_image
import discord
import pandas as pd
import io

class TeamStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='team_stats')
    async def team_stats(self, ctx):
        teams_df = get_team_stats()
        # Convert DataFrame to image
        img = create_team_table_image(teams_df)
        file = discord.File(io.BytesIO(img), filename="team_stats.png")
        await ctx.send(content="**Current Team Stats:**", file=file)

def setup(bot):
    bot.add_cog(TeamStats(bot))
