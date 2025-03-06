# cogs/team_management.py
import discord
from discord.ext import commands
from models.team import Team
from models.player import Player

class TeamManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def create_team(self, ctx, name: str, captain: discord.Member):
        """Create a new team (Admin only)"""
        try:
            await Team.create_team(name, captain.id)
            await ctx.respond(f"Team '{name}' created with captain {captain.display_name}", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error creating team: {str(e)}", ephemeral=True)

    @discord.slash_command()
    @commands.has_permissions(administrator=True)
    async def add_player_to_team(self, ctx, team_name: str, player: discord.Member):
        """Add a player to a team (Admin only)"""
        try:
            await Team.add_player(team_name, player.id)
            await ctx.respond(f"Added {player.display_name} to team '{team_name}'", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error adding player: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(TeamManagementCog(bot))
