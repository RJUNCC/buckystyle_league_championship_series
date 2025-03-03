# cogs/admin.py
import discord
from discord.commands import Option
from models.player import Player
import os
from dotenv import load_dotenv

load_dotenv()

class AdminCog(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(
        guild_ids=[int(os.getenv("SERVER_ID"))],  # Add your server ID
        name="sync",
        description="Sync commands to this server"
    )
    @discord.default_permissions(administrator=True)
    async def sync(self, ctx: discord.ApplicationContext):
        """Sync commands"""
        try:
            await ctx.defer(ephemeral=True)
            await self.bot.sync_commands(guild_ids=[ctx.guild.id])
            await ctx.followup.send("✅ Commands synced!", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.slash_command(
        guild_ids=[int(os.getenv("SERVER_ID"))],
        name="cleanup_availability",
        description="Remove legacy availability data"
    )
    @discord.default_permissions(administrator=True)
    async def cleanup_availability(self, ctx: discord.ApplicationContext):
        """Cleanup old entries"""
        try:
            await ctx.defer(ephemeral=True)
            result = await Player.remove_old_availability()
            await ctx.followup.send(f"✅ {result}", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.slash_command(
        guild_ids=[int(os.getenv("SERVER_ID"))],
        name="nuclear_cleanup",
        description="Reset ALL availability data"
    )
    @discord.default_permissions(administrator=True)
    async def nuclear_cleanup(self, ctx: discord.ApplicationContext):
        """Full reset"""
        try:
            await ctx.defer(ephemeral=True)
            result = await Player.clear_all_availability()
            await ctx.followup.send(f"✅ {result}", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(AdminCog(bot))
