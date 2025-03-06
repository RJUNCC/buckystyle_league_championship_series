# discord_bot/cogs/ballchasing.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import requests

load_dotenv()

class BallchasingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("TOKEN")
        self.base_url = "https://ballchasing.com/api"

    @discord.slash_command(name="set_ballchasing_group")
    @commands.has_permissions(administrator=True)
    async def set_current_group(self, ctx, group_id: str):
        """Set the current Ballchasing group ID for the season"""
        try:
            # Verify the group exists
            response = requests.get(f"{self.base_url}/group/{group_id}", headers={"Authorization": self.api_key})
            if response.status_code != 200:
                return await ctx.respond("Invalid group ID or API error.", ephemeral=True)

            # Update the environment variable
            os.environ["CURRENT_GROUP_ID"] = group_id
            await ctx.respond(f"Current Ballchasing group ID updated to {group_id}", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error updating group ID: {str(e)}", ephemeral=True)

    @discord.slash_command(name="get_ballchasing_stats")
    async def get_group_stats(self, ctx):
        """Get stats for the current Ballchasing group"""
        try:
            group_id = os.getenv("CURRENT_GROUP_ID")
            if not group_id:
                return await ctx.respond("No current group ID set. Use /set_ballchasing_group first.", ephemeral=True)

            response = requests.get(f"{self.base_url}/group/{group_id}/stats/players", headers={"Authorization": self.api_key})
            if response.status_code != 200:
                return await ctx.respond("Error fetching group stats.", ephemeral=True)

            stats = response.json()
            # Process and display stats here
            # This is a simplified example, you might want to format this data better
            await ctx.respond(f"Stats for group {group_id}:\n``````", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error fetching group stats: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(BallchasingCog(bot))
