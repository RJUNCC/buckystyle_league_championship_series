# cogs/statistics.py
import discord
from discord.ext import commands
import os
import sys
# from ballchasing_api import BallchasingAPI
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.process import Process

class StatisticsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.process = Process()

    @discord.slash_command(name="player_statistics")
    async def player_stats(self, ctx, player: discord.Member):
        """View statistics for a specific player"""
        try:
            df, _ = self.process.process_player_data()
            player_stats = df[df['Player'] == player.display_name]
            
            if player_stats.empty:
                return await ctx.respond(f"No statistics found for {player.display_name}", ephemeral=True)

            embed = discord.Embed(title=f"Stats for {player.display_name}", color=discord.Color.blue())
            for column in player_stats.columns:
                if column != 'Player':
                    embed.add_field(name=column, value=player_stats[column].values[0])

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error retrieving player stats: {str(e)}", ephemeral=True)

    @discord.slash_command(name="team_statistics")
    async def team_stats(self, ctx, team_name: str):
        """View statistics for a specific team"""
        try:
            df = self.process.process_team_data()
            team_stats = df[df['Team'] == team_name]
            
            if team_stats.empty:
                return await ctx.respond(f"No statistics found for team {team_name}", ephemeral=True)

            embed = discord.Embed(title=f"Stats for {team_name}", color=discord.Color.green())
            for column in team_stats.columns:
                if column != 'Team':
                    embed.add_field(name=column, value=team_stats[column].values[0])

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error retrieving team stats: {str(e)}", ephemeral=True)

    @discord.slash_command(name="stat_leaderboard")
    async def leaderboard(self, ctx, stat: str):
        """View top players for a specific statistic"""
        try:
            df, _ = self.process.process_player_data()
            if stat not in df.columns:
                return await ctx.respond(f"Invalid statistic. Choose from: {', '.join(df.columns[1:])}", ephemeral=True)

            top_players = df.sort_values(by=stat, ascending=False).head(10)
            
            embed = discord.Embed(title=f"Top Players - {stat}", color=discord.Color.gold())
            for i, (_, player) in enumerate(top_players.iterrows(), 1):
                embed.add_field(name=f"{i}. {player['Player']}", value=f"{player[stat]}", inline=False)

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error retrieving leaderboard: {str(e)}", ephemeral=True)

    @discord.slash_command(name="update_all_stats")
    async def update_stats(self, ctx):
        """Update all statistics from Ballchasing API"""
        try:
            self.process.process_player_data()
            self.process.process_team_data()
            await ctx.respond("Statistics updated successfully!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error updating statistics: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(StatisticsCog(bot))
