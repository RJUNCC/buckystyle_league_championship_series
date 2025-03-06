# discord_bot/cogs/playoff_management.py
import discord
from discord.ext import commands
from models.playoff import Playoff
from models.season import Season
from models.team import Team

class PlayoffManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="start_season_playoffs")
    @commands.has_permissions(administrator=True)
    async def start_playoffs(self, ctx):
        """Start the playoffs for the current season"""
        try:
            current_season = await Season.get_current_season()
            if not current_season:
                return await ctx.respond("There is no active season.", ephemeral=True)

            # Get top 8 teams based on standings
            top_teams = await Team.get_top_teams(8)
            if len(top_teams) < 8:
                return await ctx.respond("Not enough teams for playoffs. Need at least 8 teams.", ephemeral=True)

            await Playoff.create_bracket(current_season["number"], [team["name"] for team in top_teams])
            await ctx.respond(f"Playoffs for Season {current_season['number']} have started!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error starting playoffs: {str(e)}", ephemeral=True)

    @discord.slash_command(name="update_playoff_match_result")
    @commands.has_permissions(administrator=True)
    async def update_playoff_match(self, ctx, round_number: int, match_number: int, winner: str):
        """Update the result of a playoff match"""
        try:
            current_season = await Season.get_current_season()
            if not current_season:
                return await ctx.respond("There is no active season.", ephemeral=True)

            await Playoff.update_match(current_season["number"], round_number, match_number - 1, winner)
            await ctx.respond(f"Playoff match updated. Winner: {winner}", ephemeral=True)

            # Check if playoffs are completed
            playoff_winner = await Playoff.get_playoff_winner(current_season["number"])
            if playoff_winner:
                await ctx.send(f"🏆 Congratulations to {playoff_winner} for winning Season {current_season['number']}!")
        except Exception as e:
            await ctx.respond(f"Error updating playoff match: {str(e)}", ephemeral=True)

    @discord.slash_command(name="view_current_playoff_bracket")
    async def view_playoff_bracket(self, ctx):
        """View the current playoff bracket"""
        try:
            current_season = await Season.get_current_season()
            if not current_season:
                return await ctx.respond("There is no active season.", ephemeral=True)

            bracket = await Playoff.get_current_bracket(current_season["number"])
            if not bracket:
                return await ctx.respond("No active playoff bracket found for the current season.", ephemeral=True)

            embed = discord.Embed(title=f"Playoff Bracket - Season {current_season['number']}", color=discord.Color.gold())
            for round in bracket["rounds"]:
                round_text = ""
                for i, match in enumerate(round["matches"], 1):
                    round_text += f"Match {i}: {match['team1']} vs {match['team2']}\n"
                    if match['winner']:
                        round_text += f"Winner: {match['winner']}\n"
                    round_text += "\n"
                embed.add_field(name=f"Round {round['round_number']}", value=round_text, inline=False)

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error viewing playoff bracket: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(PlayoffManagementCog(bot))
