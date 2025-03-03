import discord
from discord.ext import tasks
from discord.ui import Select, View, Button
from datetime import datetime, timedelta, time
import pytz
from models.player import Player
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


class AvailabilityCog(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_selections = {}

class AvailabilityCog(discord.Cog):
    @discord.slash_command()
    async def set_availability(self, ctx: discord.ApplicationContext):
        """Set availability using dropdowns"""
        try:
            await ctx.defer(ephemeral=True)
            original_msg = await ctx.interaction.original_response()

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
            
            date_msg = await ctx.followup.send("**Step 1/3:** Select available dates", view=date_view)
            await date_view.wait()
            
            if not date_select.values:
                return await date_msg.edit(content="❌ Date selection timed out", view=None)

            # Step 2: Start Time
            start_view = TimeSelectorView("Start")
            start_msg = await ctx.followup.send("**Step 2/3:** Select START time", view=start_view)
            await start_view.wait()
            
            if not start_view.confirmed:
                return await start_msg.edit(content="❌ Start time selection timed out", view=None)

            # Step 3: End Time
            end_view = TimeSelectorView("End")
            end_msg = await ctx.followup.send("**Step 3/3:** Select END time", view=end_view)
            await end_view.wait()
            
            if not end_view.confirmed:
                return await end_msg.edit(content="❌ End time selection timed out", view=None)

            # Validate and save
            start_time = start_view.get_time()
            end_time = end_view.get_time()
            
            if end_time <= start_time:
                end_time = time(end_time.hour + 12, end_time.minute)  # Handle overnight
                
            if end_time <= start_time:
                return await original_msg.edit(content="❌ End time must be after start time")

            await Player.update_availability(
                ctx.author.id,
                date_select.values,
                f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
            )
            
            # Cleanup messages
            await original_msg.edit(content="✅ Availability set successfully!")
            await date_msg.delete()
            await start_msg.delete()
            await end_msg.delete()

        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)





    @discord.slash_command()
    async def view_availability(self, ctx: discord.ApplicationContext):
        """View availability calendar"""
        try:
            await ctx.defer(ephemeral=True)
            all_players = await Player.get_all_players()
            
            embed = discord.Embed(title="📅 Team Availability", color=discord.Color.blue())
            schedule = defaultdict(lambda: defaultdict(list))

            for player in all_players:
                member = ctx.guild.get_member(player["_id"])
                if not member or "availability" not in player:
                    continue
                    
                # Modified structure handling
                for entry in player["availability"]:
                    date_str = entry["date"].strftime("%a %b %d")
                    start = entry["start"].strftime("%I:%M %p").lstrip("0")
                    end = entry["end"].strftime("%I:%M %p").lstrip("0")
                    
                    if entry["end"].date() > entry["start"].date():
                        end += " (next day)"
                    
                    schedule[date_str][member.display_name].append(f"{start} - {end}")
                        
            for date in sorted(schedule.keys(), key=lambda d: datetime.strptime(d, "%a %b %d")):
                entries = []
                for member, times in schedule[date].items():
                    entries.append(f"**{member}**\n" + "\n".join(times))
                
                embed.add_field(
                    name=f"__{date}__",
                    value="\n\n".join(entries) or "No availability",
                    inline=False
                )

            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.followup.send(f"❌ Error: {str(e)}", ephemeral=True)



    
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

