# discord_bot/cogs/season_summary.py
import discord
from discord.ext import commands
from models.season import Season
from models.team import Team
from models.player import Player
from models.playoff import Playoff

class SeasonSummaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def generate_season_summary(self, season_number):
        season = await Season.get_season(season_number)
        if not season:
            raise ValueError(f"Season {season_number} not found")

        teams = await Team.get_all_teams_stats(season_number)
        top_players = await Player.get_top_players(season_number, limit=10)
        playoff_winner = await Playoff.get_playoff_winner(season_number)

        return {
            "season": season,
            "teams": teams,
            "top_players": top_players,
            "playoff_winner": playoff_winner
        }

    @discord.slash_command(name="view_season_summary")
    async def view_season_summary(self, ctx, season_number: int = None):
        """View a summary of the specified season or the current season"""
        try:
            if season_number is None:
                current_season = await Season.get_current_season()
                if not current_season:
                    return await ctx.respond("There is no active season.", ephemeral=True)
                season_number = current_season["number"]

            summary = await self.generate_season_summary(season_number)

            embed = discord.Embed(title=f"Season {season_number} Summary", color=discord.Color.blue())
            
            # Season Info
            embed.add_field(name="Season Dates", value=f"Start: {summary['season']['start_date'].strftime('%Y-%m-%d')}\nEnd: {summary['season']['end_date'].strftime('%Y-%m-%d') if summary['season']['end_date'] else 'Ongoing'}", inline=False)

            # Team Standings
            standings = "\n".join([f"{i+1}. {team['name']} - Wins: {team['wins']}, Losses: {team['losses']}" for i, team in enumerate(summary['teams'][:5])])
            embed.add_field(name="Top 5 Team Standings", value=standings, inline=False)

            # Top Players
            top_players = "\n".join([f"{i+1}. {player['name']} - {player['top_stat_name']}: {player['top_stat_value']}" for i, player in enumerate(summary['top_players'][:5])])
            embed.add_field(name="Top 5 Players", value=top_players, inline=False)

            # Playoff Winner
            if summary['playoff_winner']:
                embed.add_field(name="Playoff Winner", value=summary['playoff_winner'], inline=False)

            await ctx.respond(embed=embed)

        except Exception as e:
            await ctx.respond(f"Error generating season summary: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(SeasonSummaryCog(bot))
