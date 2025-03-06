# discord_bot/cogs/admin.py
import discord
from discord.ext import commands
from models.player import Player

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="admin_sync_commands")
    @discord.default_permissions(administrator=True)
    async def sync(self, ctx):
        """Sync slash commands (Admin only)"""
        try:
            await self.bot.sync_commands()
            await ctx.respond("✅ Commands synced!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.slash_command(name="admin_cleanup_availability")
    @discord.default_permissions(administrator=True)
    async def cleanup_availability(self, ctx):
        """Remove old availability data (Admin only)"""
        try:
            result = await Player.remove_old_availability()
            await ctx.respond(f"✅ {result}", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(AdminCog(bot))
