# cogs/scheduling.py
import discord
from discord.ext import commands
from models.scheduler import Scheduler
from datetime import datetime, timedelta
from models.player import Player

class SchedulingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="set_player_schedule")
    async def set_availability(self, ctx, day: str, start_time: str, end_time: str):
        """Set your availability for a specific day"""
        try:
            player_id = ctx.author.id
            availability = await Player.get_availability(player_id)
            
            if day not in availability:
                availability[day] = []
            
            availability[day].append({"start": start_time, "end": end_time})
            
            await Player.set_availability(player_id, availability)
            await ctx.respond(f"Availability set for {day} from {start_time} to {end_time}", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error setting availability: {str(e)}", ephemeral=True)

    @discord.slash_command(name="view_player_schedule")
    async def view_availability(self, ctx):
        """View your current availability"""
        try:
            player_id = ctx.author.id
            availability = await Player.get_availability(player_id)
            
            if not availability:
                return await ctx.respond("You haven't set any availability yet.", ephemeral=True)
            
            embed = discord.Embed(title="Your Availability", color=discord.Color.blue())
            for day, slots in availability.items():
                value = "\n".join([f"{slot['start']} - {slot['end']}" for slot in slots])
                embed.add_field(name=day, value=value, inline=False)
            
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error viewing availability: {str(e)}", ephemeral=True)

    @discord.slash_command(name="suggest_match_schedule")
    @commands.has_permissions(administrator=True)
    async def suggest_match_times(self, ctx, team1: str, team2: str, date: str):
        """Suggest match times for two teams on a specific date"""
        try:
            match_date = datetime.strptime(date, "%Y-%m-%d").date()
            possible_slots = await Scheduler.find_match_times(team1, team2, match_date)
            
            if not possible_slots:
                return await ctx.respond("No suitable time slots found for the given teams and date.", ephemeral=True)
            
            embed = discord.Embed(title=f"Suggested Match Times: {team1} vs {team2}", description=f"Date: {date}", color=discord.Color.green())
            for i, slot in enumerate(possible_slots, 1):
                embed.add_field(name=f"Option {i}", value=f"{slot['start']} - {slot['end']}", inline=False)
            
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error suggesting match times: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(SchedulingCog(bot))
