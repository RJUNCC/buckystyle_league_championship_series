# discord_bot/cogs/season_management.py
import discord
from discord.ext import commands
from models.season import Season
from models.team import Team
from models.player import Player
from datetime import datetime

class SeasonManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="start_new_season")
    @commands.has_permissions(administrator=True)
    async def start_new_season(self, ctx, ballchasing_group_id: str):
        """Start a new season"""
        try:
            current_season = await Season.get_current_season()
            if current_season:
                await ctx.respond("There's already an active season. End it first before starting a new one.", ephemeral=True)
                return

            all_seasons = await Season.get_all_seasons()
            new_season_number = len(all_seasons) + 1

            await Season.create_season(new_season_number, datetime.now(), ballchasing_group_id)
            
            # Reset team standings and player stats here
            await Team.reset_all_standings()
            await Player.reset_all_stats()

            await ctx.respond(f"Season {new_season_number} started successfully!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error starting new season: {str(e)}", ephemeral=True)

    @discord.slash_command(name="end_current_season")
    @commands.has_permissions(administrator=True)
    async def end_current_season(self, ctx):
        """End the current season"""
        try:
            await Season.end_current_season()
            await ctx.respond("Current season ended successfully!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error ending current season: {str(e)}", ephemeral=True)

    @discord.slash_command(name="view_current_season_info")
    async def view_season_info(self, ctx):
        """View information about the current season"""
        try:
            current_season = await Season.get_current_season()
            if not current_season:
                await ctx.respond("There is no active season.", ephemeral=True)
                return

            embed = discord.Embed(title=f"Season {current_season['number']} Information", color=discord.Color.blue())
            embed.add_field(name="Start Date", value=current_season['start_date'].strftime("%Y-%m-%d"), inline=False)
            embed.add_field(name="Ballchasing Group ID", value=current_season['ballchasing_group_id'], inline=False)

            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error viewing season info: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(SeasonManagementCog(bot))
