import discord
from discord.ext import tasks, commands
from discord.ui import Select, View, Button
from datetime import datetime, timedelta, time
import pytz
from models.player import Player
from models.team import Team
import os
from dotenv import load_dotenv
from collections import defaultdict
import asyncio

load_dotenv()

# Date formatting helper
def get_week_dates():
    today = datetime.now().date()
    return [
        (today + timedelta(days=i)).strftime("%A (%b %d)").replace(" 0", " ")
        for i in range(7)
    ]

DAYS_WITH_DATES = get_week_dates()

class TimeSelectorView(View):
    def __init__(self, time_type: str):
        super().__init__(timeout=120)
        self.time_type = time_type
        self.hour = None
        self.minute = None
        self.period = None
        self.confirmed = False
        
        # Hour dropdown (1-12)
        self.hour_select = Select(
            placeholder=f"{time_type} Hour",
            options=[discord.SelectOption(label=str(i)) for i in range(1, 13)]
        )
        self.hour_select.callback = self.hour_callback
        self.add_item(self.hour_select)
        
        # Minute dropdown (00, 15, 30, 45)
        self.minute_select = Select(
            placeholder=f"{time_type} Minute",
            options=[discord.SelectOption(label=f"{i:02}") for i in [0, 15, 30, 45]]
        )
        self.minute_select.callback = self.minute_callback
        self.add_item(self.minute_select)
        
        # AM/PM dropdown
        self.period_select = Select(
            placeholder=f"{time_type} Period",
            options=[discord.SelectOption(label=period) for period in ["AM", "PM"]]
        )
        self.period_select.callback = self.period_callback
        self.add_item(self.period_select)
        
        # Confirm button
        self.confirm_button = Button(
            label=f"Confirm {time_type}",
            style=discord.ButtonStyle.green,
            disabled=True
        )
        self.confirm_button.callback = self.confirm_callback
        self.add_item(self.confirm_button)

    async def hour_callback(self, interaction: discord.Interaction):
        self.hour = self.hour_select.values[0]
        self.check_complete()
        await interaction.response.defer()
        await interaction.edit_original_response(view=self)

    async def minute_callback(self, interaction: discord.Interaction):
        self.minute = self.minute_select.values[0]
        self.check_complete()
        await interaction.response.defer()
        await interaction.edit_original_response(view=self)

    async def period_callback(self, interaction: discord.Interaction):
        self.period = self.period_select.values[0]
        self.check_complete()
        await interaction.response.defer()
        await interaction.edit_original_response(view=self)

    def check_complete(self):
        self.confirm_button.disabled = not all([self.hour, self.minute, self.period])

    async def confirm_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.confirmed = True
        self.stop()

    def get_time(self) -> time:
        hour = int(self.hour)
        if self.period == "PM" and hour < 12:
            hour += 12
        elif self.period == "AM" and hour == 12:
            hour = 0
        return time(hour, int(self.minute))

class AvailabilityCog(commands.Cog):
    @discord.slash_command(name="set_player_availability")
    async def set_availability(self, ctx: discord.ApplicationContext):
        """Set availability using dropdowns"""
        try:
            # Check if player is on a team
            team = await Team.get_team_by_player(ctx.author.id)
            if not team:
                return await ctx.respond("You must be on a team to set availability", ephemeral=True)
            
            await ctx.defer(ephemeral=True)
            
            # Step 1: Date Selection
            date_view = View(timeout=120)
            date_select = Select(
                placeholder="Select dates...",
                options=[discord.SelectOption(label=day) for day in DAYS_WITH_DATES],
                min_values=1,
                max_values=7
            )
            
            async def date_callback(interaction: discord.Interaction):
                await interaction.response.defer()
                date_view.stop()
            
            date_select.callback = date_callback
            date_view.add_item(date_select)
            
            date_msg = await ctx.followup.send("**Step 1/3:** Select available dates", view=date_view, ephemeral=True)
            await date_view.wait()
            
            if not date_select.values:
                return await ctx.followup.send("❌ Date selection timed out", ephemeral=True)

            # Step 2: Start Time
            start_view = TimeSelectorView("Start")
            start_msg = await ctx.followup.send("**Step 2/3:** Select START time", view=start_view, ephemeral=True)
            await start_view.wait()
            
            if not start_view.confirmed:
                return await ctx.followup.send("❌ Start time selection timed out", ephemeral=True)

            # Step 3: End Time
            end_view = TimeSelectorView("End")
            end_msg = await ctx.followup.send("**Step 3/3:** Select END time", view=end_view, ephemeral=True)
            await end_view.wait()
            
            if not end_view.confirmed:
                return await ctx.followup.send("❌ End time selection timed out", ephemeral=True)

            # Validate and save
            start_time = start_view.get_time()
            end_time = end_view.get_time()
            
            if end_time <= start_time:
                end_time = (datetime.combine(datetime.now().date(), end_time) + timedelta(days=1)).time()
                
            if end_time <= start_time:
                return await ctx.followup.send("❌ End time must be after start time", ephemeral=True)

            # Convert times to strings
            start_str = start_time.strftime('%I:%M %p')
            end_str = end_time.strftime('%I:%M %p')

            # Update the database
            await Player.update_availability(
                ctx.author.id,
                date_select.values,
                start_str,
                end_str
            )
            
            # Final confirmation
            await ctx.followup.send(f"✅ Availability set: {start_str} - {end_str} for {', '.join(date_select.values)}", ephemeral=True)

        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)





    @discord.slash_command(name="view_player_availability")
    async def view_availability(self, ctx: discord.ApplicationContext):
        """View team availability calendar"""
        try:
            await ctx.defer(ephemeral=True)
            all_teams = await Team.get_all_teams()
            
            embed = discord.Embed(title="📅 Team Availability", color=discord.Color.blue())

            for team in all_teams:
                schedule = defaultdict(list)
                for player_id in team["players"]:
                    availability = await Player.get_player_availability(player_id)
                    member = ctx.guild.get_member(player_id)
                    for entry in availability:
                        date_str = entry["date"].strftime("%Y-%m-%d")
                        schedule[date_str].append(f"{member.display_name}: {entry['start']} - {entry['end']}")

                if schedule:
                    embed.add_field(
                        name=f"__{team['name']}__",
                        value="\n".join([f"**{date}**\n" + "\n".join(times) for date, times in schedule.items()]),
                        inline=False
                    )

            await ctx.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @tasks.loop(hours=1)
    async def remove_past_availability(self):
        await Player.remove_past_availability()
    
    @discord.slash_command()
    async def clear_availability(self, ctx: discord.ApplicationContext):
        """Clear your availability"""
        await Player.clear_player_availability(ctx.author.id)
        await ctx.respond("✅ Availability cleared", ephemeral=True)

    def cog_unload(self):
        self.reminder.cancel()
        self.reset_availability.cancel()

class TimeRangeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Add Time Ranges")
        self.time_ranges = []
        
        # Use only valid modal components (InputText)
        self.add_item(
            discord.ui.InputText(
                label="Time Ranges (HH:MM AM/PM - HH:MM AM/PM)",
                placeholder="Example:\n8:00 AM - 12:00 PM\n8:00 PM - 1:00 AM",
                style=discord.InputTextStyle.long
            )
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            for line in self.children[0].value.split("\n"):
                start, end = map(str.strip, line.split("-"))
                self.time_ranges.append((start, end))
            await interaction.response.defer()
            self.stop()
        except Exception as e:
            await interaction.response.send_message(f"❌ Invalid format: {str(e)}", ephemeral=True)


def setup(bot):
    bot.add_cog(AvailabilityCog(bot))