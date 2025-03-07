# discord_bot/cogs/admin.py
import discord
from discord.ext import commands
from models.player import Player
import os

class AdminCog(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("AdminCog initialized")  # Debug print

    @discord.slash_command()  # Remove any guild_ids parameter
    @commands.has_permissions(administrator=True)
    async def admin_sync(self, ctx):
        """Force sync all commands (Admin only)"""
        try:
            print("Admin sync command executed")  # Debug print
            await ctx.defer(ephemeral=True)
            synced = await self.bot.sync_commands(guild_ids=[ctx.guild.id])
            await ctx.followup.send(f"✅ Synced {len(synced)} commands to this server!", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.slash_command()  # Remove any guild_ids parameter
    @commands.has_permissions(administrator=True)
    async def admin_cleanup(self, ctx):
        """Remove old availability data (Admin only)"""
        try:
            await ctx.defer(ephemeral=True)
            result = await Player.remove_old_availability()
            await ctx.followup.send(f"✅ {result}", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(AdminCog(bot))
    print("AdminCog setup complete")  # Debug print
