# cogs/series_management.py
import discord
import os
from discord.ext import commands
from models.series import Series
from models.team import Team
from models.playoff import Playoff
from models.player import Player
from datetime import datetime

class SeriesManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def schedule_series(self, ctx, team1: str, team2: str, date: str, time: str, is_playoff: bool = False):
        """Schedule a series between two teams"""
        try:
            # Parse date and time
            date_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            
            # Verify teams exist
            team1_data = await Team.get_team_by_name(team1)
            team2_data = await Team.get_team_by_name(team2)
            if not team1_data or not team2_data:
                return await ctx.respond("One or both teams do not exist.", ephemeral=True)

            # Create series
            series = await Series.create_series(team1, team2, date_time, is_playoff)
            
            # Create Discord channel for the series
            channel = await self.create_series_channel(ctx.guild, team1, team2, date_time, series.inserted_id)
            
            await ctx.respond(f"Series scheduled between {team1} and {team2} on {date_time.strftime('%Y-%m-%d %H:%M')}. Channel created: {channel.mention}", ephemeral=True)
            
            # Notify team captains
            await self.notify_captains(team1_data, team2_data, date_time, channel)

        except ValueError:
            await ctx.respond("Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error scheduling series: {str(e)}", ephemeral=True)

    async def create_series_channel(self, guild, team1, team2, date_time, series_id):
        channel_name = f"{team1}-vs-{team2}-{date_time.strftime('%m-%d')}"
        category = discord.utils.get(guild.categories, name="Series Matches")
        if not category:
            category = await guild.create_category("Series Matches")

        channel = await guild.create_text_channel(channel_name, category=category)
        await Series.update_channel_id(series_id, channel.id)
        return channel

    async def notify_captains(self, team1, team2, date_time, channel):
        for team in [team1, team2]:
            captain = self.bot.get_user(team['captain_id'])
            if captain:
                await captain.send(f"A series has been scheduled for your team on {date_time.strftime('%Y-%m-%d %H:%M')}. Channel: {channel.mention}")

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def report_game_result(self, ctx, team1_score: int, team2_score: int):
        """Report the result of a game in a series"""
        try:
            series = await Series.get_series_by_channel(ctx.channel.id)
            if not series:
                return await ctx.respond("This command can only be used in a series channel.", ephemeral=True)

            winner = series['team1'] if team1_score > team2_score else series['team2']
            score = {series['team1']: team1_score, series['team2']: team2_score}

            series_winner = await Series.report_game_result(series['_id'], winner, score)

            await ctx.respond(f"Game result recorded: {series['team1']} {team1_score} - {team2_score} {series['team2']}")

            if series_winner:
                await ctx.send(f"🏆 Series Winner: {series_winner}!")
                await self.finalize_series(ctx.guild, series)

        except Exception as e:
            await ctx.respond(f"Error reporting game result: {str(e)}", ephemeral=True)

    async def finalize_series(self, guild, series):
        channel = guild.get_channel(series['channel_id'])
        if channel:
            await channel.send("This series has concluded. This channel will be archived in 24 hours.")

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def view_upcoming_series(self, ctx):
        """View all upcoming series"""
        try:
            upcoming_series = await Series.get_upcoming_series()
            if not upcoming_series:
                return await ctx.respond("No upcoming series scheduled.", ephemeral=True)

            embed = discord.Embed(title="Upcoming Series", color=discord.Color.blue())
            for series in upcoming_series:
                embed.add_field(
                    name=f"{series['team1']} vs {series['team2']}",
                    value=f"Date: {series['date'].strftime('%Y-%m-%d %H:%M')}\nPlayoff: {'Yes' if series['is_playoff'] else 'No'}",
                    inline=False
                )

            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            await ctx.respond(f"Error viewing upcoming series: {str(e)}", ephemeral=True)

    @discord.slash_command()
    async def view_standings(self, ctx):
        """View current league standings"""
        try:
            standings = await Team.get_standings()
            
            embed = discord.Embed(title="League Standings", color=discord.Color.blue())
            for i, team in enumerate(standings, 1):
                embed.add_field(
                    name=f"{i}. {team['name']}",
                    value=f"Wins: {team['wins']} | Losses: {team['losses']} | Series Played: {team['series_played']}",
                    inline=False
                )

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error viewing standings: {str(e)}", ephemeral=True)

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def create_playoff_bracket(self, ctx):
        """Create the playoff bracket based on current standings"""
        try:
            standings = await Team.get_standings()
            if len(standings) < 8:
                return await ctx.respond("Not enough teams for playoffs", ephemeral=True)

            top_8_teams = [team['name'] for team in standings[:8]]
            await Playoff.create_bracket(top_8_teams)
            await ctx.respond("Playoff bracket created!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error creating playoff bracket: {str(e)}", ephemeral=True)

    @discord.slash_command()
    async def view_playoff_bracket(self, ctx):
        """View the current playoff bracket"""
        try:
            bracket = await Playoff.get_current_bracket()
            if not bracket:
                return await ctx.respond("No active playoff bracket found", ephemeral=True)

            embed = discord.Embed(title=f"Playoff Bracket - Round {bracket['round']}", color=discord.Color.gold())
            for i, match in enumerate(bracket['matches'], 1):
                embed.add_field(
                    name=f"Match {i}",
                    value=f"{match['team1']} vs {match['team2']}\nWinner: {match['winner'] or 'TBD'}",
                    inline=False
                )

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error viewing playoff bracket: {str(e)}", ephemeral=True)

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def update_playoff_match(self, ctx, match_number: int, winner: str):
        """Update a playoff match result"""
        try:
            await Playoff.update_bracket(match_number - 1, winner)
            await ctx.respond(f"Playoff match {match_number} updated. Winner: {winner}", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error updating playoff match: {str(e)}", ephemeral=True)

    # Update the report_game_result method to update standings
    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def report_game_result(self, ctx, team1_score: int, team2_score: int):
        """Report the result of a game in a series"""
        try:
            series = await Series.get_series_by_channel(ctx.channel.id)
            if not series:
                return await ctx.respond("This command can only be used in a series channel.", ephemeral=True)

            winner = series['team1'] if team1_score > team2_score else series['team2']
            loser = series['team2'] if team1_score > team2_score else series['team1']
            score = {series['team1']: team1_score, series['team2']: team2_score}

            series_winner = await Series.report_game_result(series['_id'], winner, score)

            # Update standings
            await Team.update_standings(winner, True)
            await Team.update_standings(loser, False)

            await ctx.respond(f"Game result recorded: {series['team1']} {team1_score} - {team2_score} {series['team2']}")

            if series_winner:
                await ctx.send(f"🏆 Series Winner: {series_winner}!")
                await self.finalize_series(ctx.guild, series)

        except Exception as e:
            await ctx.respond(f"Error reporting game result: {str(e)}", ephemeral=True)

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def report_player_stats(self, ctx, player: discord.Member, goals: int, assists: int, saves: int, shots: int):
        """Report individual player stats for a game"""
        try:
            await Player.update_stats(player.id, goals, assists, saves, shots)
            await ctx.respond(f"Stats updated for {player.display_name}", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error updating player stats: {str(e)}", ephemeral=True)

    # Update the report_game_result method to include team stat updates
    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def report_game_result(self, ctx, team1_score: int, team2_score: int):
        """Report the result of a game in a series"""
        try:
            series = await Series.get_series_by_channel(ctx.channel.id)
            if not series:
                return await ctx.respond("This command can only be used in a series channel.", ephemeral=True)

            winner = series['team1'] if team1_score > team2_score else series['team2']
            loser = series['team2'] if team1_score > team2_score else series['team1']
            score = {series['team1']: team1_score, series['team2']: team2_score}

            series_winner = await Series.report_game_result(series['_id'], winner, score)

            # Update standings and team stats
            await Team.update_standings(winner, True)
            await Team.update_standings(loser, False)
            await Team.update_team_stats(series['team1'], team1_score, team2_score)
            await Team.update_team_stats(series['team2'], team2_score, team1_score)

            await ctx.respond(f"Game result recorded: {series['team1']} {team1_score} - {team2_score} {series['team2']}")

            if series_winner:
                await ctx.send(f"🏆 Series Winner: {series_winner}!")
                await self.finalize_series(ctx.guild, series)

        except Exception as e:
            await ctx.respond(f"Error reporting game result: {str(e)}", ephemeral=True)

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def set_current_group(self, ctx, group_id: str):
        """Set the current Ballchasing group ID for the season"""
        try:
            os.environ["CURRENT_GROUP_ID"] = group_id
            await ctx.respond(f"Current group ID updated to {group_id}", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error updating group ID: {str(e)}", ephemeral=True)


def setup(bot):
    bot.add_cog(SeriesManagementCog(bot))
