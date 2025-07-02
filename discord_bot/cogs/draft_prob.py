# cogs/draft_prob.py
import discord
import json
from discord.ext import commands
import asyncio
import random
from collections import defaultdict
from typing import Dict, List, Tuple, NamedTuple
from datetime import datetime, timedelta
import discord.utils

# Import database functions
try:
    from models.scheduling import save_session, delete_session, get_all_active_sessions, load_session, SchedulingSession as DBSchedulingSession
except ImportError:
    print("Warning: scheduling module not found. Database persistence disabled.")
    save_session = lambda x: None
    load_session = lambda x: None
    delete_session = lambda x: None
    get_all_active_active_sessions = lambda: []

class Player(NamedTuple):
    name: str
    tier: int

class DraftResult(NamedTuple):
    draft_order: List[Tuple[int, str, int]]
    eliminated: List[Tuple[str, int]]



class DaySelect(discord.ui.Select):
    def __init__(self, options, user_id, session, parent_view):
        super().__init__(
            placeholder="Select a day to set your availability",
            options=options
        )
        self.user_id = user_id
        self.session = session
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
                
            selected_day = self.values[0]
            date_info = self.session.get_date_info(selected_day)
            time_view = TimeSelectionView(self.user_id, selected_day, self.session, self.parent_view)
            
            embed = discord.Embed(
                title=f"📅 Setting Availability for {date_info['full_date']}",
                description=f"Select all times you're available on **{date_info['full_date']}**:",
                color=0x0099ff
            )
            
            await interaction.response.edit_message(
                embed=embed,
                view=time_view
            )
        except Exception as e:
            print(f"Error in day_select: {e}")
            try:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
            except:
                pass

class TimeSelectionView(discord.ui.View):
    def __init__(self, user_id, day, session, parent_view):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.day = day
        self.session = session
        self.parent_view = parent_view
        self.selected_times = set()
        
    @discord.ui.select(
        placeholder="Select available times (you can select multiple)",
        options=[
            discord.SelectOption(label="6:00 PM", value="18:00"),
            discord.SelectOption(label="7:00 PM", value="19:00"),
            discord.SelectOption(label="8:00 PM", value="20:00"),
            discord.SelectOption(label="9:00 PM", value="21:00"),
            discord.SelectOption(label="10:00 PM", value="22:00"),
            discord.SelectOption(label="11:00 PM", value="23:00"),
            discord.SelectOption(label="12:00 AM", value="00:00"),
        ],
        max_values=7,  # Updated to match the number of options
        min_values=0
    )
    async def time_select(self, select: discord.ui.Select, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
                
            self.selected_times = set(select.values)
            
            embed = discord.Embed(
                title=f"📅 {self.day} Availability",
                color=0x0099ff
            )
            
            if self.selected_times:
                times_display = ", ".join([self.format_time_display(t) for t in sorted(self.selected_times)])
                embed.description = f"**Selected times:** {times_display}\n\nClick 'Confirm Times' to save these times or select different ones."
            else:
                embed.description = f"**No times selected** (not available)\n\nClick 'Not Available' to confirm or select times above."
            
            await interaction.response.edit_message(
                embed=embed,
                view=self
            )
        except Exception as e:
            print(f"Error in time_select: {e}")
            try:
                await interaction.response.send_message("Error selecting times", ephemeral=True)
            except:
                pass
    
    def format_time_display(self, time_24h):
        try:
            hour = int(time_24h.split(':')[0])
            minute = time_24h.split(':')[1]
            
            if hour == 0:
                return f"12:{minute} AM"
            elif hour < 12:
                return f"{hour}:{minute} AM"
            elif hour == 12:
                return f"12:{minute} PM"
            else:
                return f"{hour-12}:{minute} PM"
        except:
            return time_24h
    
    @discord.ui.button(label="Confirm Times", style=discord.ButtonStyle.green)
    async def confirm_times(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
                
            # Save the times for this day
            if self.user_id not in self.session.player_schedules:
                self.session.player_schedules[self.user_id] = {}
                
            self.session.player_schedules[self.user_id][self.day] = list(self.selected_times)
            self.session = save_session(self.session)
            
            # Go back to day selection with updated info
            await self.return_to_day_selection(interaction, f"✅ **{self.day}** times saved!")
                
        except Exception as e:
            print(f"Error in confirm_times: {e}")
            try:
                await interaction.response.send_message("Error confirming times", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="Not Available", style=discord.ButtonStyle.red)
    async def not_available(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
                
            if self.user_id not in self.session.player_schedules:
                self.session.player_schedules[self.user_id] = {}
                
            self.session.player_schedules[self.user_id][self.day] = []
            self.session = save_session(self.session)
            
            # Go back to day selection with updated info
            await self.return_to_day_selection(interaction, f"✅ **{self.day}** marked as not available!")
            
        except Exception as e:
            print(f"Error in not_available: {e}")
            try:
                await interaction.response.send_message("Error setting unavailable", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="Available All Day", style=discord.ButtonStyle.blurple)
    async def all_day(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
                
            # Set all available times (6 PM to 12 AM - 7 hour slots)
            all_times = ["18:00", "19:00", "20:00", "21:00", "22:00", "23:00", "00:00"]
                
            if self.user_id not in self.session.player_schedules:
                self.session.player_schedules[self.user_id] = {}
                
            self.session.player_schedules[self.user_id][self.day] = all_times
            self.session = save_session(self.session)
            
            # Go back to day selection with updated info
            await self.return_to_day_selection(interaction, f"✅ **{self.day}** set to all day available!")
            
        except Exception as e:
            print(f"Error in all_day: {e}")
            try:
                await interaction.response.send_message("Error setting all day", ephemeral=True)
            except:
                pass
    
    @discord.ui.button(label="← Back to Day Selection", style=discord.ButtonStyle.secondary)
    async def back_to_days(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
            
            await self.return_to_day_selection(interaction, "Select another day to set your availability:")
            
        except Exception as e:
            print(f"Error in back_to_days: {e}")
            try:
                await interaction.response.send_message("Error going back", ephemeral=True)
            except:
                pass
    
    async def return_to_day_selection(self, interaction, message):
        """Return to the day selection view with updated progress"""
        schedule = self.session.player_schedules.get(self.user_id, {})
        days_set = len(schedule)
        
        embed = discord.Embed(
            title="📅 Set Your Weekly Availability",
            description=f"{message}\n\n**Progress: {days_set}/7 days completed**\n\nSelect another day to continue or finalize when all 7 days are set.",
            color=0x0099ff if days_set < 7 else 0x00ff00
        )
        
        # Show current status for each day with actual dates
        status_text = ""
        for date_info in self.session.schedule_dates:
            day_name = date_info['day_name']
            day_display = f"{date_info['day_name']}, {date_info['date']}"
            
            if day_name in schedule:
                if not schedule[day_name]:
                    status_text += f"**{day_display}:** ❌ Not available\n"
                elif len(schedule[day_name]) >= 6:  # Updated threshold for 1-hour intervals (6+ out of 7 slots = "all day")
                    status_text += f"**{day_display}:** ✅ All day\n"
                else:
                    status_text += f"**{day_display}:** ✅ {len(schedule[day_name])} time slots\n"
            else:
                status_text += f"**{day_display}:** ⏳ Not set\n"
        
        embed.add_field(name="📋 Current Schedule", value=status_text, inline=False)
        
        await interaction.response.edit_message(
            embed=embed,
            view=self.parent_view
        )

class DaySelectionView(discord.ui.View):
    def __init__(self, user_id, session):
        super().__init__(timeout=600)  # 10 minute timeout
        self.user_id = user_id
        self.session = session
        
        # Create dynamic options based on actual dates
        self.create_day_options()
        
    def create_day_options(self):
        """Create dropdown options with actual dates"""
        options = []
        for date_info in self.session.schedule_dates:
            # Format: "Monday, 06/29"
            label = f"{date_info['day_name']}, {date_info['date']}"
            options.append(
                discord.SelectOption(
                    label=label,
                    value=date_info['day_name'],  # Still use day name as value for compatibility
                    description=date_info['full_date'],  # "Monday, June 29"
                    emoji="📅"
                )
            )
        
        # Add the select to the view
        self.add_item(DaySelect(options, self.user_id, self.session, self))
    
    @discord.ui.button(label="View My Schedule", style=discord.ButtonStyle.secondary)
    async def view_schedule(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
                
            if self.user_id not in self.session.player_schedules:
                await interaction.response.send_message("You haven't set any times yet!", ephemeral=True)
                return
                
            schedule = self.session.player_schedules[self.user_id]
            schedule_text = "**Your Schedule for the Next Week:**\n\n"
            
            days_set = 0
            for date_info in self.session.schedule_dates:
                day_name = date_info['day_name']
                day_display = f"{date_info['day_name']}, {date_info['date']}"
                
                if day_name in schedule:
                    days_set += 1
                    if not schedule[day_name]:
                        schedule_text += f"**{day_display}:** ❌ Not available\n"
                    elif len(schedule[day_name]) >= 20:
                        schedule_text += f"**{day_display}:** ✅ All day available\n"
                    else:
                        times = [self.format_time_display(t) for t in sorted(schedule[day_name])]
                        schedule_text += f"**{day_display}:** ✅ {', '.join(times)}\n"
                else:
                    schedule_text += f"**{day_display}:** ⏳ Not set\n"
            
            schedule_text += f"\n**Progress:** {days_set}/7 days completed"
            
            if days_set == 7:
                schedule_text += "\n🎉 **Ready to finalize!** Use the 'Finalize Schedule' button."
                
            embed = discord.Embed(
                title="📋 Your Weekly Schedule",
                description=schedule_text,
                color=0x0099ff
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in view_schedule: {e}")
            try:
                await interaction.response.send_message("Error viewing schedule", ephemeral=True)
            except:
                pass
    
    def format_time_display(self, time_24h):
        try:
            hour = int(time_24h.split(':')[0])
            minute = time_24h.split(':')[1]
            
            if hour == 0:
                return f"12:{minute} AM"
            elif hour < 12:
                return f"{hour}:{minute} AM"
            elif hour == 12:
                return f"12:{minute} PM"
            else:
                return f"{hour-12}:{minute} PM"
        except:
            return time_24h
    
    async def finalize_schedule_callback(self, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return
            
            # Convert schedule_state to the format expected by DBSchedulingSession
            player_schedule_for_db = {}
            for day_name, day_data in self.schedule_state.items():
                status = day_data.get('status')
                if status == 'not_available':
                    player_schedule_for_db[day_name] = []
                elif status == 'all_day':
                    player_schedule_for_db[day_name] = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']
                elif status == 'partial':
                    selected_times = [time for time, selected in day_data.items() if time != 'status' and selected]
                    player_schedule_for_db[day_name] = selected_times
                # If status is None (not set) or 'unsure', it's not added to player_schedule_for_db

            # Check if all 7 days are set
            if len(player_schedule_for_db) < 7:
                await interaction.response.send_message(f"Please set all 7 days before finalizing! You have {len(player_schedule_for_db)}/7 days set.", ephemeral=True)
                return

            # Update the session object with the new schedule
            self.session.player_schedules[str(self.user_id)] = player_schedule_for_db
            self.session.players_responded.add(str(self.user_id))
            self.session = save_session(self.session) # Save to DB

            # Find the cog to access bot and finalize_scheduling method
            draft_cog = None
            for cog in interaction.client.cogs.values():
                if hasattr(cog, 'active_sessions') and int(self.session.channel_id) in cog.active_sessions:
                    draft_cog = cog
                    break
            
            if draft_cog:
                channel = draft_cog.bot.get_channel(self.session.channel_id)
                remaining = self.session.expected_players - len(self.session.players_responded)
                
                if remaining > 0:
                    await channel.send(f"📝 {interaction.user.display_name} finalized their schedule. Waiting for {remaining} more players...")
                
                await interaction.response.edit_message(
                    content="✅ **Schedule finalized!** Thank you for submitting your availability.",
                    embed=None,
                    view=None
                )
                
                # Check if all schedules are complete
                if self.session.is_complete():
                    await draft_cog.finalize_scheduling(channel, self.session)
            else:
                await interaction.response.send_message("Error finding scheduling session", ephemeral=True)
                
        except Exception as e:
            import traceback
            traceback.print_exc() # Print full traceback to console
            await interaction.response.send_message(f"An unexpected error occurred during finalization: {e}", ephemeral=True)

class ConfirmationView(discord.ui.View):
    def __init__(self, session, game_time_info, cog):
        super().__init__(timeout=600)  # 10 minute timeout
        self.session = session
        self.game_time_info = game_time_info
        self.cog = cog
        
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm_game(self, button: discord.ui.Button, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # Check if user is part of this game
        if user_id not in self.session.player_schedules:
            await interaction.response.send_message("You're not part of this scheduled game!", ephemeral=True)
            return
            
        self.session.confirmations[user_id] = True
        self.session = save_session(self.session)
        confirmed = sum(1 for c in self.session.confirmations.values() if c)
        total = len(self.session.player_schedules)
        
        await interaction.response.send_message(f"✅ You confirmed the game time! ({confirmed}/{total} confirmed)", ephemeral=True)
        
        # Check if everyone confirmed
        if confirmed >= self.session.expected_players:
            channel = self.cog.bot.get_channel(self.session.channel_id)
            final_embed = discord.Embed(
                title="🎮 Game Confirmed!",
                description=f"**{self.game_time_info['full_date']} at {self.game_time_info['time']}**",
                color=0x00ff00
            )
            final_embed.add_field(
                name="Status",
                value="✅ All players confirmed! Game is scheduled.",
                inline=False
            )
            
            await channel.send("@everyone")
            await channel.send(embed=final_embed)
            
            # Clean up session
            if self.session.channel_id in self.cog.active_sessions:
                del self.cog.active_sessions[self.session.channel_id]
                delete_session(self.session.channel_id)
    
    @discord.ui.button(label="❌ Can't Make It", style=discord.ButtonStyle.red)
    async def decline_game(self, button: discord.ui.Button, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        if user_id not in self.session.player_schedules:
            await interaction.response.send_message("You're not part of this scheduled game!", ephemeral=True)
            return
            
        self.session.confirmations[user_id] = False
        
        # Reset this player's status so they can resubmit
        if str(user_id) in self.session.player_schedules:
            del self.session.player_schedules[str(user_id)]
        if str(user_id) in self.session.players_responded:
            self.session.players_responded.remove(str(user_id))
        
        self.session.players_responded.remove(str(user_id))
        self.session = save_session(self.session)

        await interaction.response.send_message(
            "❌ You declined the game time. Please update your schedule using `/my_schedule` and set more accurate times.",
            ephemeral=True
        )
        
        channel = self.cog.bot.get_channel(self.session.channel_id)
        await channel.send(f"⚠️ {interaction.user.display_name} can't make the proposed time. They need to update their schedule. Use `/my_schedule` to resubmit availability.")

class DraftLottery:
    def __init__(self):
        self.players = {
            1: ['Sym', 'Distill'],
            2: ['Supe', 'Wavy', 'Ank', 'Pullis', 'Beckham'],
            3: ['Elhon', 'Aryba', 'Turtle']
        }
        
        self.weights = {
            1: [60, 50, 35, 25, 15, 10, 6, 4],
            2: [6, 8, 12, 16, 18, 16, 14, 10],
            3: [4, 6, 10, 14, 18, 22, 26, 30]
        }
    
    def get_all_players(self) -> List[Player]:
        all_players = []
        for tier, names in self.players.items():
            all_players.extend([Player(name, tier) for name in names])
        return all_players
    
    def conduct_draft(self) -> DraftResult:
        remaining = self.get_all_players()
        draft_order = []
        
        for pick in range(8):
            if not remaining:
                break
            
            tier1_remaining = [p for p in remaining if p.tier == 1]
            remaining_picks = 8 - pick
            tier1_boost = self._calculate_tier1_boost(len(tier1_remaining), remaining_picks)
            
            probabilities = []
            for player in remaining:
                base_weight = self.weights[player.tier][pick] if pick < len(self.weights[player.tier]) else 1
                if player.tier == 1:
                    base_weight *= tier1_boost
                probabilities.append(base_weight)
            
            selected_player = self._weighted_random_choice(remaining, probabilities)
            draft_order.append((pick + 1, selected_player.name, selected_player.tier))
            remaining.remove(selected_player)
        
        eliminated = [(p.name, p.tier) for p in remaining]
        return DraftResult(draft_order, eliminated)
    
    def _calculate_tier1_boost(self, tier1_count: int, remaining_picks: int) -> float:
        if tier1_count == 0:
            return 1.0
        if tier1_count >= remaining_picks:
            return 50.0
        elif tier1_count == remaining_picks - 1:
            return 10.0
        elif tier1_count == remaining_picks - 2:
            return 3.0
        else:
            return 1.0
    
    def _weighted_random_choice(self, items: List[Player], weights: List[float]) -> Player:
        total_weight = sum(weights)
        random_value = random.random() * total_weight
        
        cumulative_weight = 0
        for item, weight in zip(items, weights):
            cumulative_weight += weight
            if random_value <= cumulative_weight:
                return item
        return items[-1]
    
    def run_simulation(self, num_simulations: int = 1000) -> Dict:
        results = {
            'picks': defaultdict(lambda: [0] * 8),
            'eliminations': defaultdict(int),
            'tier1_eliminations': 0,
            'total_runs': num_simulations
        }
        
        for _ in range(num_simulations):
            draft_result = self.conduct_draft()
            
            for pick, player, tier in draft_result.draft_order:
                results['picks'][player][pick - 1] += 1
            
            for player, tier in draft_result.eliminated:
                results['eliminations'][player] += 1
                if tier == 1:
                    results['tier1_eliminations'] += 1
        
        return results

class DraftLotteryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lottery = DraftLottery()
        self.last_result = None
        self.active_sessions = {}
        self.background_task = None  # Track the task for proper cleanup
        
        # Don't create the task in __init__ - use cog_load instead
    
    async def cog_load(self):
        """Called when the cog is loaded - safer place for async tasks"""
        try:
            self.background_task = asyncio.create_task(self.load_active_sessions())
            print("✅ Background task for loading sessions started")
        except Exception as e:
            print(f"Error starting background task: {e}")
    
    async def cog_unload(self):
        """Called when the cog is unloaded - clean up tasks"""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                print("✅ Background task cancelled successfully")
            except Exception as e:
                print(f"Error cancelling background task: {e}")
    
    async def load_active_sessions(self):
        """Load all active sessions from database on startup"""
        try:
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            await asyncio.sleep(2)  # Additional safety delay
            
            active_sessions = get_all_active_sessions()
            for db_session in active_sessions:
                session = DBSchedulingSession.from_db(db_session)
                self.active_sessions[int(db_session.channel_id)] = session
                print(f"✅ Loaded scheduling session for channel {db_session.channel_id}")
                
        except asyncio.CancelledError:
            # Handle graceful cancellation
            print("📝 Session loading cancelled")
            raise
        except Exception as e:
            print(f"Error loading sessions: {e}")

    def get_pick_emoji(self, pick: int) -> str:
        if pick <= 2:
            return "⭐"
        elif pick <= 4:
            return "🔥" 
        elif pick <= 6:
            return "✨"
        else:
            return "💫"

    # ======================
    # DRAFT LOTTERY COMMANDS
    # ======================

    @discord.slash_command(name="draft", description="Run the dramatic draft lottery presentation")
    async def run_draft_lottery(self, ctx):
        """Run the dramatic draft lottery presentation"""
        
        # Initial announcement
        embed = discord.Embed(
            title="🏀 DRAFT LOTTERY COMMENCING 🏀",
            description="**The fate of 10 players will be decided...**\n\n" +
                       "**Tier 1:** Sym, Distill *(Protected)*\n" +
                       "**Tier 2:** Supe, Wavy, Ank, Pullis, Beckham\n" +
                       "**Tier 3:** Elhon, Aryba, Turtle\n\n" +
                       "*Only 8 will make the draft... 2 will be eliminated...*",
            color=0x1f8b4c
        )
        embed.set_footer(text="Preparing lottery balls... 🎱")
        
        message = await ctx.respond(embed=embed)
        await asyncio.sleep(3)
        
        # Dramatic countdown
        for i in range(3, 0, -1):
            embed = discord.Embed(
                title="🎲 LOTTERY BEGINNING IN...",
                description=f"# {i}",
                color=0xe74c3c
            )
            await ctx.edit(embed=embed)
            await asyncio.sleep(1)
        
        # "Drawing" message
        embed = discord.Embed(
            title="🎱 DRAWING LOTTERY BALLS...",
            description="*The rocket league gods are deciding...*",
            color=0xf39c12
        )
        await ctx.edit(embed=embed)
        await asyncio.sleep(2)
        
        # Conduct the actual lottery
        result = self.lottery.conduct_draft()
        self.last_result = result
        
        # Calculate the actual probabilities each player had for their position
        def get_pick_probability(player_name: str, pick_position: int, is_eliminated: bool = False) -> float:
            # Find player's tier
            player_tier = None
            for tier, names in self.lottery.players.items():
                if player_name in names:
                    player_tier = tier
                    break
            
            if player_tier is None:
                return 0.0
            
            if is_eliminated:
                return 20.0  # Default elimination chance
            else:
                # For drafted players, use their weight for that pick position
                base_weights = self.lottery.weights[player_tier]
                if pick_position <= len(base_weights):
                    return base_weights[pick_position - 1]
                else:
                    return 1.0
        
        # Initialize running lists
        eliminated_list = ""
        draft_list = ""
        
        # First, dramatically reveal the eliminated players
        if result.eliminated:
            await asyncio.sleep(2)
            embed = discord.Embed(
                title="💀 THE ELIMINATED PLAYERS ARE...",
                description="*Two players will not make the draft...*",
                color=0xe74c3c
            )
            await ctx.edit(embed=embed)
            await asyncio.sleep(4)
            
            for i, (player, tier) in enumerate(result.eliminated):
                elimination_chance = get_pick_probability(player, 0, is_eliminated=True)
                eliminated_list += f"💀 **{player}** ({elimination_chance:.1f}%)\n"
                
                # Update the same message for elimination
                embed = discord.Embed(
                    title=f"❌ ELIMINATED PLAYER #{i+1}",
                    description=f"## 💀 **{player}**\n*Elimination chance: {elimination_chance:.1f}%*",
                    color=0xe74c3c
                )
                embed.add_field(
                    name="❌ ELIMINATED PLAYERS",
                    value=eliminated_list,
                    inline=False
                )
                await ctx.edit(embed=embed)
                await asyncio.sleep(6)
        
        # Transition message
        await asyncio.sleep(2)
        embed = discord.Embed(
            title="🎯 NOW FOR THE DRAFT ORDER...",
            description="*Counting down from 8th to 1st pick...*",
            color=0x3498db
        )
        if eliminated_list:
            embed.add_field(
                name="❌ ELIMINATED PLAYERS",
                value=eliminated_list,
                inline=False
            )
        await ctx.edit(embed=embed)
        await asyncio.sleep(4)
        
        # Sort draft order by pick number in reverse (8 to 1)
        sorted_draft = sorted(result.draft_order, key=lambda x: x[0], reverse=True)
        
        for i, (pick, player, tier) in enumerate(sorted_draft):
            pick_emoji = self.get_pick_emoji(pick)
            pick_chance = get_pick_probability(player, pick)
            
            # Add current pick to draft list (maintain 1-8 order)
            draft_entry = f"{pick_emoji} **Pick #{pick}:** `{player}` ({pick_chance:.1f}%)\n"
            
            # Build the draft list in proper 1-8 order
            all_picks = []
            if draft_list:
                for line in draft_list.split('\n'):
                    if line.strip():
                        all_picks.append(line)
            all_picks.append(draft_entry.strip())
            
            # Sort by pick number to maintain 1-8 order
            def extract_pick_num(line):
                try:
                    return int(line.split('#')[1].split(':')[0])
                except:
                    return 999
            
            all_picks.sort(key=extract_pick_num)
            draft_list = '\n'.join(all_picks)
            
            # Update the same message for each pick
            if pick <= 2:
                embed = discord.Embed(
                    title=f"🎉 #{pick} OVERALL PICK! 🎉",
                    description=f"## {pick_emoji} **{player}**\n*Pick chance: {pick_chance:.1f}%*",
                    color=0xffd700
                )
                embed.add_field(
                    name="🏆 DRAFT ORDER SO FAR",
                    value=draft_list,
                    inline=False
                )
                if eliminated_list:
                    embed.add_field(
                        name="❌ ELIMINATED PLAYERS",
                        value=eliminated_list,
                        inline=False
                    )
                await ctx.edit(embed=embed)
                await asyncio.sleep(8)
            elif pick <= 4:
                embed = discord.Embed(
                    title=f"🔥 #{pick} Overall Pick",
                    description=f"## {pick_emoji} **{player}**\n*Pick chance: {pick_chance:.1f}%*",
                    color=0xff6b35
                )
                embed.add_field(
                    name="🏆 DRAFT ORDER SO FAR",
                    value=draft_list,
                    inline=False
                )
                if eliminated_list:
                    embed.add_field(
                        name="❌ ELIMINATED PLAYERS",
                        value=eliminated_list,
                        inline=False
                    )
                await ctx.edit(embed=embed)
                await asyncio.sleep(7)
            else:
                embed = discord.Embed(
                    title=f"#{pick} Overall Pick",
                    description=f"## {pick_emoji} **{player}**\n*Pick chance: {pick_chance:.1f}%*",
                    color=0x3498db
                )
                embed.add_field(
                    name="🏆 DRAFT ORDER SO FAR",
                    value=draft_list,
                    inline=False
                )
                if eliminated_list:
                    embed.add_field(
                        name="❌ ELIMINATED PLAYERS",
                        value=eliminated_list,
                        inline=False
                    )
                await ctx.edit(embed=embed)
                await asyncio.sleep(7)
        
        # Final summary message
        await asyncio.sleep(3)
        
        final_embed = discord.Embed(
            title="🏆 FINAL DRAFT LOTTERY RESULTS 🏆",
            description="*The lottery has spoken!*",
            color=0x1f8b4c
        )
        
        final_embed.add_field(
            name="🏆 FINAL DRAFT ORDER",
            value=draft_list,
            inline=False
        )
        
        if eliminated_list:
            final_embed.add_field(
                name="❌ ELIMINATED PLAYERS",
                value=eliminated_list,
                inline=False
            )
        
        # Add tier breakdown
        tier_counts = {1: 0, 2: 0, 3: 0}
        for _, _, tier in result.draft_order:
            tier_counts[tier] += 1
        
        breakdown = f"Tier 1: {tier_counts[1]}/2\nTier 2: {tier_counts[2]}/5\nTier 3: {tier_counts[3]}/3"
        final_embed.add_field(name="📊 Draft Breakdown", value=breakdown, inline=True)
        
        final_embed.set_footer(text="The lottery has spoken! 🎱")
        
        await ctx.edit(embed=final_embed)

    @discord.slash_command(name="sim", description="Run simulation analysis")
    async def run_simulation(self, ctx, runs: int = 1000):
        """Run simulation analysis"""
        if runs < 1 or runs > 10000:
            await ctx.respond("❌ Please choose between 1 and 10,000 simulations.", ephemeral=True)
            return
        
        # Loading message
        embed = discord.Embed(
            title="🔄 Running Simulation...",
            description=f"Simulating {runs:,} draft lotteries...",
            color=0xf39c12
        )
        await ctx.respond(embed=embed)
        
        # Run simulation
        results = self.lottery.run_simulation(runs)
        
        # Build results embed
        embed = discord.Embed(
            title=f"📊 SIMULATION RESULTS ({runs:,} runs)",
            color=0x3498db
        )
        
        # Tier 1 protection verification
        tier1_elim_pct = (results['tier1_eliminations'] / runs) * 100
        embed.add_field(
            name="🛡️ Tier 1 Protection",
            value=f"Eliminations: {results['tier1_eliminations']:,} / {runs:,} ({tier1_elim_pct:.3f}%)",
            inline=False
        )
        
        # Player statistics
        all_players = []
        for tier, names in self.lottery.players.items():
            all_players.extend([(name, tier) for name in names])
        
        stats_text = "```\nPlayer   Tier  Elim%  Avg Pick  Top 2%\n" + "-" * 40 + "\n"
        
        for player, tier in sorted(all_players, key=lambda x: x[1]):
            elim_pct = (results['eliminations'][player] / runs) * 100
            
            total_picks = sum(results['picks'][player])
            if total_picks > 0:
                weighted_sum = sum(count * (pos + 1) for pos, count in enumerate(results['picks'][player]))
                avg_pick = weighted_sum / total_picks
            else:
                avg_pick = 0
            
            top2_count = results['picks'][player][0] + results['picks'][player][1]
            top2_pct = (top2_count / runs) * 100
            
            stats_text += f"{player:<8} {tier:<4} {elim_pct:<6.1f} {avg_pick:<8.1f} {top2_pct:<6.1f}\n"
        
        stats_text += "```"
        
        embed.add_field(name="📈 Player Statistics", value=stats_text, inline=False)
        embed.set_footer(text="Higher Avg Pick = Later in draft | Elim% = Elimination rate")
        
        await ctx.edit(embed=embed)

    @discord.slash_command(name="weights", description="Show the probability weights used in the lottery")
    async def show_weights(self, ctx):
        """Show the probability weights used in the lottery"""
        embed = discord.Embed(
            title="🎯 LOTTERY PROBABILITY WEIGHTS",
            description="Higher numbers = higher chance of selection at that pick position",
            color=0x9b59b6
        )
        
        weights_text = "```\nPick#  Tier1  Tier2  Tier3\n" + "-" * 25 + "\n"
        for i in range(8):
            weights_text += f"#{i+1:<4} {self.lottery.weights[1][i]:<6} {self.lottery.weights[2][i]:<6} {self.lottery.weights[3][i]:<6}\n"
        weights_text += "```"
        
        embed.add_field(name="📊 Weight Distribution", value=weights_text, inline=False)
        embed.add_field(
            name="🛡️ Protection System",
            value="Tier 1 players get automatic boosts (3x, 10x, 50x) when elimination risk increases",
            inline=False
        )
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="tiers", description="Show player tier assignments")
    async def show_tiers(self, ctx):
        """Show player tier assignments"""
        embed = discord.Embed(
            title="🏀 PLAYER TIER ASSIGNMENTS",
            description="Players are grouped by skill level with different draft probabilities",
            color=0x1f8b4c
        )
        
        for tier, players in self.lottery.players.items():
            protection = " *(Protected)*" if tier == 1 else ""
            player_list = ", ".join(players)
            
            embed.add_field(
                name=f"Tier {tier}{protection}",
                value=player_list,
                inline=False
            )
        
        embed.set_footer(text="Tier 1 players have protection against elimination")
        await ctx.respond(embed=embed)

    @discord.slash_command(name="last_draft", description="Show the last draft result")
    async def show_last_draft(self, ctx):
        """Show the last draft result"""
        if not self.last_result:
            await ctx.respond("❌ No draft has been run yet. Use `/draft` to run a lottery!", ephemeral=True)
            return
        
        result = self.last_result
        
        # Build draft order text
        draft_text = ""
        for pick, player, tier in result.draft_order:
            pick_emoji = self.get_pick_emoji(pick)
            draft_text += f"{pick_emoji} **Pick #{pick}:** `{player}`\n"
        
        embed = discord.Embed(
            title="🏆 LAST DRAFT RESULT",
            description=draft_text,
            color=0x1f8b4c
        )
        
        # Add elimination section if any
        if result.eliminated:
            elim_text = ""
            for player, tier in result.eliminated:
                elim_text += f"💀 `{player}`\n"
            
            embed.add_field(
                name="❌ ELIMINATED PLAYERS",
                value=elim_text,
                inline=False
            )
        
        # Add tier breakdown
        tier_counts = {1: 0, 2: 0, 3: 0}
        for _, _, tier in result.draft_order:
            tier_counts[tier] += 1
        
        breakdown = f"Tier 1: {tier_counts[1]}/2\nTier 2: {tier_counts[2]}/5\nTier 3: {tier_counts[3]}/3"
        embed.add_field(name="📊 Draft Breakdown", value=breakdown, inline=True)
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="tournament_seeding", description="Generate dramatic tournament seeding for 8 teams")
    @commands.has_permissions(administrator=True)
    async def tournament_seeding(self, ctx):
        """Generate dramatic tournament seeding ceremony"""
        try:
            # Team names
            teams = [
                "YNs", "Team 2", "Mulignans", "16 Keycaps",
                "Team 5", "Mounties", "Team 7", "Ice Truck Killers"
            ]
            
            # Shuffle teams randomly
            shuffled_teams = teams.copy()
            random.shuffle(shuffled_teams)
            
            # Create seeding dictionary
            seeding = {}
            for i, team in enumerate(shuffled_teams, 1):
                seeding[i] = team
            
            # Initial announcement
            embed = discord.Embed(
                title="🏆 TOURNAMENT SEEDING CEREMONY 🏆",
                description="The moment you've all been waiting for...\nThe seeds have been determined!\n\nDrumroll please... 🥁🥁🥁",
                color=0xffd700
            )
            await ctx.respond(embed=embed)
            await asyncio.sleep(3)
            
            # Dramatic phrases for each seed
            dramatic_phrases = [
                "👑 Taking the throne as our #1 seed...",
                "🥈 Claiming the prestigious #2 position...",
                "🥉 Securing a strong #3 seed...",
                "⭐ Earning the #4 spot with determination...",
                "🔥 Fighting their way to the #5 seed...",
                "💪 Proving their worth as the #6 seed...",
                "⚡ Showing resilience as our #7 seed...",
                "🎯 Rounding out our bracket as the #8 seed..."
            ]
            
            seeding_text = ""
            
            # Announce each seed dramatically
            for seed in range(1, 9):
                seeding_text += f"**SEED #{seed}**: {seeding[seed]}\n"
                
                embed = discord.Embed(
                    title="🎯 SEEDING ANNOUNCEMENT 🎯",
                    description=f"⚡ {dramatic_phrases[seed-1]}\n\n**SEED #{seed}: {seeding[seed]}**",
                    color=0x00ff00 if seed <= 4 else 0xff6600
                )
                
                if seeding_text:
                    embed.add_field(
                        name="🏆 SEEDS ANNOUNCED SO FAR",
                        value=seeding_text,
                        inline=False
                    )
                
                await ctx.edit(embed=embed)
                await asyncio.sleep(4)
            
            # Final summary
            final_embed = discord.Embed(
                title="🎊 LET THE TOURNAMENT BEGIN! 🎊",
                description="All seeds and matchups have been determined!",
                color=0x00ff00
            )
            
            final_embed.add_field(
                name="🏆 FINAL SEEDINGS",
                value=seeding_text,
                inline=False
            )
            
            final_embed.set_footer(text="Good luck to all teams! 🍀")
            
            await ctx.edit(embed=final_embed)
            
        except Exception as e:
            await ctx.channel.send(f"Error generating tournament seeding: {str(e)}")

    # ======================
    # SCHEDULING COMMANDS
    # ======================

    @discord.slash_command(name="schedule_game", description="Start a game scheduling session between two teams")
    @commands.has_permissions(administrator=True)
    async def schedule_game(self, ctx, team1: str, team2: str):
        """Start a game scheduling session"""
        channel_id = ctx.channel.id
        
        # Check if there's already an active session in this channel
        if channel_id in self.active_sessions:
            await ctx.respond("There's already an active scheduling session in this channel. Use `/cancel_schedule` to cancel it first.", ephemeral=True)
            return
        
        # Create new scheduling session
        session = DBSchedulingSession(channel_id=str(channel_id), team1=team1, team2=team2)
        self.active_sessions[channel_id] = session
        self.active_sessions[channel_id] = save_session(session)
        
        embed = discord.Embed(
            title="🎮 Game Scheduling Started!",
            description=(
                f"**Scheduling game between {team1} and {team2}**\n\n"
                f"📋 **What Players Need to Do:**\n"
                f"All **6 players** (3 from each team) choose an interface:\n"
                f"• `/my_schedule` - Visual calendar interface ⭐\n\n"
                f"• Times range from 6 PM to 12 AM (7 time slots)\n"
                f"• Easy buttons for 'Not Available' and 'All Day'\n\n"
                f"🎯 **Process:**\n"
                f"1️⃣ All 6 players set their weekly availability\n"
                f"2️⃣ Bot finds common times and proposes game time\n"
                f"3️⃣ All players confirm with ✅/❌ buttons\n"
                f"4️⃣ If anyone declines, they update schedule and repeat\n\n"
                f"⏳ **Progress:** Waiting for {session.expected_players} players...\n"
            ),
            color=0x00ff00
        )
        embed.set_footer(text="Use /my_schedule to start setting your availability!")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="my_schedule", description="Set your weekly availability using visual calendar interface")
    async def my_schedule(self, ctx):
        """Visual calendar-style schedule setting"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel. Start one with `/schedule_game Team1 Team2`", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        user_id = ctx.author.id
        
        # Create the visual calendar view
        view = CalendarScheduleView(user_id, session)
        
        # Allow players to reset/modify their schedule
        if str(user_id) in session.players_responded:
            embed = discord.Embed(
                title="🔄 Update Your Schedule (Calendar View)",
                description="Use the calendar below to update your availability. Click time slots to toggle them on/off.",
                color=0xffa500
            )
        else:
            embed = discord.Embed(
                title="📅 Set Your Weekly Availability (Calendar View)",
                description="Use the calendar below to set your available times. Click time slots to select them.",
                color=0x0099ff
            )
        
        # Add initial progress info
        days_completed = 0
        status_text = ""
        
        for date_info in session.schedule_dates:
            day_name = date_info['day_name']
            day_display = f"{date_info['day_name']}, {date_info['date']}"
            status_text += f"**{day_display}:** ⏳ Not set\n"
        
        embed.add_field(
            name=f"📋 Progress: {days_completed}/7 days completed",
            value=status_text,
            inline=False
        )
        
        embed.add_field(
            name="💡 How to use:",
            value=(
                "• **Green buttons** = Available times\n"
                "• **Gray buttons** = Not available\n"
                "• **All day** = Available 6PM-12AM\n"
                "• **Not Available** = Unavailable that day\n"
                "• **Unsure** = Uncertain availability"
            ),
            inline=False
        )
        
        try:
            # Send the calendar interface directly in DM
            await ctx.author.send(embed=embed, view=view)
            await ctx.respond(f"{ctx.author.mention}, check your DMs for the visual calendar interface!", ephemeral=True)
        except discord.Forbidden:
            await ctx.respond("I couldn't send you a DM. Please enable DMs from server members and try again.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error sending calendar interface: {str(e)}", ephemeral=True)

    async def finalize_scheduling(self, channel, session):
        """Find common times and start confirmation process"""
        # Ensure session is a DBSchedulingSession object
        if not isinstance(session, DBSchedulingSession):
            print(f"Error: session is not DBSchedulingSession, it is {type(session)}")
            return

        common_times = session.find_common_times()
        
        if not common_times:
            embed = discord.Embed(
                title="❌ No Common Times Found",
                description="Unfortunately, no times work for all players. Players should use `/my_schedule` to adjust their availability.",
                color=0xff0000
            )
            await channel.send(embed=embed)
            return
        
        # Pick the best time
        best_day = None
        best_time = None
        best_date_info = None
        
        for date_info in session.schedule_dates:
            day_name = date_info['day_name']
            if day_name in common_times and common_times[day_name]:
                best_day = day_name
                best_date_info = date_info
                # Prefer evening times (6 PM to 10 PM)
                for time in common_times[day_name]:
                    hour = int(time.split(':')[0])
                    if 18 <= hour <= 22:
                        best_time = time
                        break
                if not best_time:
                    best_time = common_times[day_name][0]
                break
        
        if not best_day or not best_time or not best_date_info:
            embed = discord.Embed(
                title="❌ No Suitable Time Found",
                description="Could not determine a good game time. Please adjust schedules.",
                color=0xff0000
            )
            await channel.send(embed=embed)
            return
        
        # Format time for display
        hour = int(best_time.split(':')[0])
        minute = best_time.split(':')[1]
        
        if hour == 0:
            display_time = f"12:{minute} AM"
        elif hour < 12:
            display_time = f"{hour}:{minute} AM"
        elif hour == 12:
            display_time = f"12:{minute} PM"
        else:
            display_time = f"{hour-12}:{minute} PM"
        
        game_info = {
            'day': best_day, 
            'time': display_time,
            'full_date': best_date_info['full_date'],
            'date': best_date_info['date']
        }
        
        # Create Discord Scheduled Event
        try:
            # Parse the date and time for the event
            # Example: "Monday, July 1, 2024" and "6:00 PM"
            date_str = best_date_info['full_date']
            time_str = display_time
            
            # Adjust year to current year if the month has already passed
            current_year = datetime.now().year
            # Attempt to parse with current year
            try:
                event_datetime = datetime.strptime(f"{date_str} {time_str}", "%A, %B %d, %Y %I:%M %p")
            except ValueError:
                # If parsing fails, try with next year (for cases like December scheduling for January)
                event_datetime = datetime.strptime(f"{date_str} {time_str}", "%A, %B %d, %Y %I:%M %p")
                if event_datetime < datetime.now():
                    event_datetime = event_datetime.replace(year=current_year + 1)

            event_name = f"{session.teams[0]} vs {session.teams[1]} Game"
            event_description = f"Scheduled game between {session.teams[0]} and {session.teams[1]} based on player availability."
            
            # Assuming a 1-hour game
            event_end_time = event_datetime + timedelta(hours=1)

            # Create the event
            scheduled_event = await channel.create_scheduled_event(
                name=event_name,
                start_time=event_datetime,
                end_time=event_end_time,
                description=event_description,
                entity_type=discord.EntityType.external, # Use external for general events not tied to voice/stage channels
                location=f"Discord Channel: #{channel.name}" # Or a specific game server/platform
            )
            
            embed_event_success = discord.Embed(
                title="🎉 Discord Event Created!",
                description=f"A Discord event has been created for the game: [{event_name}]({scheduled_event.url})",
                color=0x7289da
            )
            await channel.send(embed=embed_event_success)

        except discord.Forbidden:
            print(f"ERROR: Bot does not have permissions to create scheduled events in channel {channel.name} ({channel.id}).")
            await channel.send("⚠️ I don't have permission to create Discord events. Please grant me 'Manage Events' permission.")
        except Exception as e:
            print(f"ERROR: Failed to create Discord event: {e}")
            await channel.send(f"❌ An error occurred while trying to create the Discord event: {e}")

        embed = discord.Embed(
            title="🎮 Proposed Game Time",
            description=f"**{best_date_info['full_date']} at {display_time}**",
            color=0xffa500
        )
        embed.add_field(
            name="⚠️ Confirmation Required",
            value="All players must confirm this time works for them using the buttons below.",
            inline=False
        )
        embed.add_field(
            name="Available Times Found",
            value=self.format_available_times_interactive(common_times, session),
            inline=False
        )
        
        view = ConfirmationView(session, game_info, self)
        session.confirmation_message = await channel.send("@everyone", embed=embed, view=view)

    def format_available_times_interactive(self, common_times, session):
        """Format available times for display with actual dates"""
        formatted = []
        for date_info in session.schedule_dates:
            day_name = date_info['day_name']
            if day_name in common_times and common_times[day_name]:
                times = common_times[day_name]
                display_times = []
                for time in times[:5]:  # Show first 5 times
                    hour = int(time.split(':')[0])
                    minute = time.split(':')[1]
                    if hour == 0:
                        display_times.append(f"12:{minute} AM")
                    elif hour < 12:
                        display_times.append(f"{hour}:{minute} AM")
                    elif hour == 12:
                        display_times.append(f"12:{minute} PM")
                    else:
                        display_times.append(f"{hour-12}:{minute} PM")
                
                time_str = ", ".join(display_times)
                if len(times) > 5:
                    time_str += f" (+{len(times)-5} more)"
                day_display = f"{date_info['day_name']}, {date_info['date']}"
                formatted.append(f"**{day_display}:** {time_str}")
        
        return "\n".join(formatted) if formatted else "No common times found"

    @discord.slash_command(name="cancel_schedule", description="Cancel the current scheduling session")
    async def cancel_schedule(self, ctx):
        """Cancel the current scheduling session"""
        channel_id = ctx.channel.id
        
        if channel_id in self.active_sessions:
            del self.active_sessions[channel_id]
            delete_session(channel_id)
            await ctx.respond("❌ Scheduling session cancelled.")
        else:
            await ctx.respond("No active scheduling session to cancel.", ephemeral=True)

    @discord.slash_command(name="schedule_status", description="Check the status of the current scheduling session")
    async def schedule_status(self, ctx):
        """Check the status of the current scheduling session"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        remaining = session.expected_players - len(session.players_responded)
        
        embed = discord.Embed(
            title="📊 Scheduling Status",
            color=0x0099ff
        )
        embed.add_field(
            name="Progress",
            value=f"{len(session.players_responded)}/{session.expected_players} players completed their schedules",
            inline=False
        )
        
        if remaining > 0:
            embed.add_field(
                name="Remaining",
                value=f"Waiting for {remaining} more players to use `/my_schedule`",
                inline=False
            )
        else:
            embed.add_field(
                name="Status", 
                value="All schedules received! Processing game time...",
                inline=False
            )
        
        embed.add_field(
            name="Teams",
            value=f"{session.teams[0]} vs {session.teams[1]}",
            inline=False
        )
        
        await ctx.respond(embed=embed)
    
    @discord.slash_command(name="db_health", description="Check database health and connection")
    @commands.has_permissions(administrator=True)
    async def db_health(self, ctx):
        """Check database health and connection status"""
        try:
            from models.scheduling import engine, get_all_active_sessions
            from sqlalchemy import text
            import time
            
            # Test connection
            start_time = time.time()
            
            # Try a simple query with proper SQLAlchemy 2.0 syntax
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            connection_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Get database info
            db_url = str(engine.url)
            db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
            
            # Count active sessions
            try:
                active_sessions = get_all_active_sessions()
                session_count = len(active_sessions)
            except Exception as e:
                session_count = f"Error: {e}"
            
            embed = discord.Embed(
                title="🏥 Database Health Check",
                color=0x00ff00
            )
            embed.add_field(name="Database Type", value=db_type, inline=True)
            embed.add_field(name="Connection Time", value=f"{connection_time:.2f}ms", inline=True)
            embed.add_field(name="Status", value="✅ Healthy", inline=True)
            embed.add_field(name="Active Sessions", value=str(session_count), inline=True)
            embed.add_field(name="Memory Sessions", value=str(len(self.active_sessions)), inline=True)
            
            # Show database URL (masked for security)
            masked_url = db_url.split('@')[0] + '@***' if '@' in db_url else db_url
            embed.add_field(name="Database URL", value=f"`{masked_url}`", inline=False)
            
            if db_type == "PostgreSQL":
                embed.add_field(name="💾 Persistence", value="✅ Full persistence across deployments", inline=False)
            else:
                embed.add_field(name="⚠️ Persistence", value="Limited - consider upgrading to PostgreSQL", inline=False)
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="🏥 Database Health Check",
                description=f"❌ Database connection failed: {str(e)}",
                color=0xff0000
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="backup_sessions", description="Backup current scheduling sessions")
    @commands.has_permissions(administrator=True)
    async def backup_sessions(self, ctx):
        """Export current sessions for backup"""
        await ctx.defer(ephemeral=True)  # Defer the response to prevent timeouts
        try:
            import io
            
            sessions_data = {}
            
            # Get active sessions from memory
            for channel_id, session in self.active_sessions.items():
                sessions_data[str(channel_id)] = {
                    'teams': session.teams,
                    'player_schedules': session.player_schedules,
                    'players_responded': list(session.players_responded),
                    'schedule_dates': session.schedule_dates,
                    'expected_players': session.expected_players,
                    'confirmations': getattr(session, 'confirmations', {})
                }
            
            # Also get sessions from database
            try:
                db_sessions = get_all_active_sessions()
                for db_session in db_sessions:
                    if str(db_session.channel_id) not in sessions_data:
                        sessions_data[str(db_session.channel_id)] = {
                            'teams': [db_session.team1, db_session.team2],
                            'player_schedules': db_session.player_schedules or {},
                            'players_responded': db_session.players_responded or [],
                            'schedule_dates': db_session.schedule_dates or [],
                            'expected_players': db_session.expected_players,
                            'confirmations': db_session.confirmations or {}
                        }
            except Exception as e:
                print(f"Error getting database sessions: {e}")
            
            if not sessions_data:
                await ctx.followup.send("No active sessions to backup.", ephemeral=True)
                return
            
            # Create backup file
            json_data = json.dumps(sessions_data, indent=2, default=str)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sessions_backup_{timestamp}.json"
            
            file = discord.File(
                io.StringIO(json_data), 
                filename=filename
            )
            
            embed = discord.Embed(
                title="💾 Sessions Backup Created",
                description=f"Backed up {len(sessions_data)} active sessions.",
                color=0x0099ff
            )
            
            await ctx.followup.send(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            await ctx.followup.send(f"Error creating backup: {str(e)}", ephemeral=True)

    @discord.slash_command(name="debug_sessions", description="Debug database sessions")
    @commands.has_permissions(administrator=True)
    async def debug_sessions(self, ctx):
        """Debug what sessions are in database vs memory"""
        try:
            from models.scheduling import get_all_active_sessions
            
            # Get from database
            db_sessions = get_all_active_sessions()
            
            embed = discord.Embed(
                title="🔍 Session Debug",
                color=0x0099ff
            )
            
            embed.add_field(
                name="Memory Sessions",
                value=f"{len(self.active_sessions)} sessions\n" +
                    "\n".join([f"Channel {cid}" for cid in self.active_sessions.keys()]) if self.active_sessions else "None",
                inline=False
            )
            
            embed.add_field(
                name="Database Sessions", 
                value=f"{len(db_sessions)} sessions\n" +
                    
                "".join([f"Channel {s.channel_id}: {s.team1} vs {s.team2} (Active: {s.is_active})" for s in db_sessions]) if db_sessions else "None",
                inline=False
            )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"Error: {str(e)}", ephemeral=True)

    @discord.slash_command(name="reload_sessions", description="Manually reload sessions from database")
    @commands.has_permissions(administrator=True)
    async def reload_sessions(self, ctx):
        """Manually reload sessions from database"""
        embed = discord.Embed(
            title="🔄 Sessions Reloaded",
            description="",
            color=0x00ff00
        )
        try:
            from models.scheduling import get_all_active_sessions, SchedulingSession as DBSchedulingSession
            
            # Clear current sessions
            old_count = len(self.active_sessions)
            self.active_sessions.clear()
            
            # Load from database
            db_sessions = get_all_active_sessions()
            loaded_count = 0
            
            for db_session in db_sessions:
                try:
                    session = DBSchedulingSession.from_db(db_session)
                    self.active_sessions[int(db_session.channel_id)] = session
                    loaded_count += 1
                except Exception as e:
                    print(f"Error loading session {db_session.channel_id}: {e}")
                    embed.add_field(name=f"❌ Error loading {db_session.channel_id}", value=str(e), inline=False)
            
            embed.description = f"Cleared {old_count} memory sessions\nLoaded {loaded_count} from database"
            
        except Exception as e:
            embed.title = "❌ Error Reloading Sessions"
            embed.description = f"An error occurred while reloading sessions: {str(e)}"
            embed.color = 0xff0000
            
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="view_all_schedules", description="View all players' availability schedules")
    async def view_all_schedules(self, ctx):
        """View all players' schedules in the current session"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        
        if not session.player_schedules:
            await ctx.respond("No players have submitted schedules yet.", ephemeral=True)
            return
        
        # Create main embed
        embed = discord.Embed(
            title="📊 All Players' Schedules",
            description=f"**{session.teams[0]} vs {session.teams[1]}**\n{len(session.player_schedules)}/{session.expected_players} players completed",
            color=0x0099ff
        )
        
        # Time slots for reference
        time_slots = {
            '18:00': '6 PM', '19:00': '7 PM', '20:00': '8 PM', 
            '21:00': '9 PM', '22:00': '10 PM', '23:00': '11 PM', '00:00': '12 AM'
        }
        
        schedule_text = ""
        
        for user_id, player_schedule in session.player_schedules.items():
            try:
                # Get user display name
                user = self.bot.get_user(int(user_id))
                player_name = user.display_name if user else f"User {user_id}"
                
                schedule_text += f"\n**{player_name}:**\n"
                
                # Gracefully handle corrupted or non-dict schedule data
                if not isinstance(player_schedule, dict):
                    schedule_text += f"  • ⚠️ Corrupted schedule data. Please use `/my_schedule` to reset.\n\n"
                    print(f"DEBUG: Corrupted schedule data for user {user_id} in channel {channel_id}")
                    continue

                # Show availability for each day
                for date_info in session.schedule_dates:
                    day_name = date_info['day_name']
                    day_display = f"{date_info['day_name']}, {date_info['date']}"
                    
                    if day_name in player_schedule:
                        available_times = player_schedule[day_name]
                        
                        if not available_times:
                            schedule_text += f"  • {day_display}: ❌ Not available\n"
                        elif len(available_times) >= 6:
                            schedule_text += f"  • {day_display}: ✅ All day available\n"
                        else:
                            # Show specific times
                            time_display = []
                            for time_24h in available_times:
                                if time_24h in time_slots:
                                    time_display.append(time_slots[time_24h])
                            
                            if time_display:
                                schedule_text += f"  • {day_display}: ✅ {', '.join(time_display)}\n"
                            else:
                                schedule_text += f"  • {day_display}: ⚠️ Invalid times\n"
                    else:
                        schedule_text += f"  • {day_display}: ⏳ Not set\n"
                
                schedule_text += "\n"  # Add spacing between players
                
            except Exception as e:
                print(f"ERROR: Failed to process schedule for user {user_id}: {e}")
                schedule_text += f"\n**User {user_id}:** Error loading schedule (`{type(e).__name__}: {e}`)\n\n"
        
        # Split into multiple embeds if too long (Discord limit is 4096 characters)
        if len(schedule_text) > 3500:
            # Send summary first
            embed.add_field(
                name="📋 Summary",
                value=f"Schedules are too long to display in one message. Use `/schedule_summary` for a condensed view.",
                inline=False
            )
            await ctx.respond(embed=embed, ephemeral=True)
            
            # Send detailed view in chunks
            chunks = [schedule_text[i:i+3500] for i in range(0, len(schedule_text), 3500)]
            
            for i, chunk in enumerate(chunks):
                chunk_embed = discord.Embed(
                    title=f"📊 Detailed Schedules (Part {i+1}/{len(chunks)})",
                    description=chunk,
                    color=0x0099ff
                )
                await ctx.followup.send(embed=chunk_embed, ephemeral=True)
        else:
            embed.add_field(
                name="📋 Player Availability",
                value=schedule_text or "No schedules found.",
                inline=False
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="schedule_summary", description="View condensed summary of all players' availability")
    @commands.has_permissions(administrator=True)
    async def schedule_summary(self, ctx):
        """Admin command to view a condensed summary of player availability"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        
        if not session.player_schedules:
            await ctx.respond("No players have submitted schedules yet.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📊 Schedule Summary",
            description=f"**{session.teams[0]} vs {session.teams[1]}**",
            color=0x0099ff
        )
        
        # Create availability matrix
        summary_text = "```\n"
        summary_text += "Player".ljust(15) + " | "
        
        # Header with day abbreviations
        for date_info in session.schedule_dates:
            day_abbr = date_info['day_name'][:3]  # Mon, Tue, etc.
            summary_text += f"{day_abbr}".ljust(6)
        summary_text += "\n" + "-" * 65 + "\n"
        
        # Player rows
        for user_id, player_schedule in session.player_schedules.items():
            try:
                user = self.bot.get_user(int(user_id))
                player_name = (user.display_name if user else f"User{user_id}")[:14]  # Truncate long names
                
                summary_text += player_name.ljust(15) + " | "
                
                for date_info in session.schedule_dates:
                    day_name = date_info['day_name']
                    
                    if day_name in player_schedule:
                        available_times = player_schedule[day_name]
                        
                        if not available_times:
                            summary_text += "❌".ljust(6)
                        elif len(available_times) >= 6:
                            summary_text += "✅✅".ljust(6)
                        else:
                            summary_text += f"✅{len(available_times)}".ljust(6)
                    else:
                        summary_text += "⏳".ljust(6)
                
                summary_text += "\n"
                
            except Exception as e:
                summary_text += f"Error".ljust(15) + " | " + "❌".ljust(6) * 7 + "\n"
        
        summary_text += "```"
        
        embed.add_field(
            name="Legend",
            value="❌ = Not available | ✅✅ = All day | ✅3 = 3 time slots | ⏳ = Not set",
            inline=False
        )
        
        embed.add_field(
            name="Availability Matrix",
            value=summary_text,
            inline=False
        )
        
        # Add common times analysis
        common_times = session.find_common_times()
        if common_times:
            common_text = ""
            for day_name, times in common_times.items():
                date_info = session.get_date_info(day_name)
                day_display = f"{date_info['day_name']}, {date_info['date']}" if date_info else day_name
                
                time_slots = {
                    '18:00': '6PM', '19:00': '7PM', '20:00': '8PM', 
                    '21:00': '9PM', '22:00': '10PM', '23:00': '11PM', '00:00': '12AM'
                }
                
                time_display = [time_slots.get(t, t) for t in times[:3]]  # Show first 3
                if len(times) > 3:
                    time_display.append(f"+{len(times)-3} more")
                
                common_text += f"**{day_display}:** {', '.join(time_display)}\n"
            
            embed.add_field(
                name="🎯 Possible Game Times",
                value=common_text,
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ No Common Times",
                value="No times work for all players yet.",
                inline=False
            )
        
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="export_schedules", description="Export all schedules as a file")
    @commands.has_permissions(administrator=True)
    async def export_schedules(self, ctx):
        """Export all player schedules as a JSON file"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        
        if not session.player_schedules:
            await ctx.respond("No players have submitted schedules yet.", ephemeral=True)
            return
        
        try:
            import json
            import io
            from datetime import datetime
            
            # Create export data
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "teams": session.teams,
                "channel_id": str(channel_id),
                "schedule_dates": session.schedule_dates,
                "player_count": len(session.player_schedules),
                "expected_players": session.expected_players,
                "players": {}
            }
            
            # Add player data with names
            for user_id, player_schedule in session.player_schedules.items():
                try:
                    user = self.bot.get_user(int(user_id))
                    player_name = user.display_name if user else f"User {user_id}"
                    
                    export_data["players"][str(user_id)] = {
                        "name": player_name,
                        "schedule": player_schedule
                    }
                except Exception as e:
                    export_data["players"][str(user_id)] = {
                        "name": f"User {user_id}",
                        "schedule": player_schedule,
                        "error": str(e)
                    }
            
            # Create file
            json_data = json.dumps(export_data, indent=2, default=str)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"schedules_{session.teams[0].replace(' ', '_')}_vs_{session.teams[1].replace(' ', '_')}_{timestamp}.json"
            
            file = discord.File(
                io.StringIO(json_data),
                filename=filename
            )
            
            embed = discord.Embed(
                title="📁 Schedules Exported",
                description=f"Exported {len(session.player_schedules)} player schedules",
                color=0x00ff00
            )
            
            await ctx.respond(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"Error exporting schedules: {str(e)}", ephemeral=True)

class CalendarScheduleView(discord.ui.View):
    def __init__(self, user_id, session):
        super().__init__(timeout=600)  # 10 minute timeout
        self.user_id = user_id
        self.session = session  # This is now a DBSchedulingSession object
        self.current_day_index = 0  # Start with first day
        
        # Track schedule state: {day: {time: selected_state}}
        # selected_state: None, 'available', 'all_day', 'not_available', 'unsure'
        self.schedule_state = {}
        
        # Initialize schedule state from existing data if any
        # Access player_schedules directly from the DBSchedulingSession object
        existing_schedule = self.session.player_schedules.get(str(self.user_id), {})
        for date_info in self.session.schedule_dates:
            day_name = date_info['day_name']
            self.schedule_state[day_name] = {}
            
            if day_name in existing_schedule:
                existing_times = existing_schedule[day_name]
                if not existing_times:  # Empty list = not available
                    self.schedule_state[day_name]['status'] = 'not_available'
                elif len(existing_times) >= 6:  # 6+ slots = all day
                    self.schedule_state[day_name]['status'] = 'all_day'
                else:
                    self.schedule_state[day_name]['status'] = 'partial'
                    # Mark specific times as available
                    for time_slot in ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']:
                        self.schedule_state[day_name][time_slot] = time_slot in existing_times
            else:
                self.schedule_state[day_name]['status'] = None
        
        self.create_calendar_buttons()
    
    def create_calendar_buttons(self):
        """Create a simplified calendar that fits Discord's 5-row limit"""
        # We'll use a day-by-day approach instead of a full grid
        # Show current day being edited
        
        current_day_index = getattr(self, 'current_day_index', 0)
        if current_day_index >= len(self.session.schedule_dates):
            current_day_index = 0
            
        current_date_info = self.session.schedule_dates[current_day_index]
        current_day_name = current_date_info['day_name']
        
        # Row 0: Day navigation
        prev_button = discord.ui.Button(
            label="◀ Prev Day", 
            style=discord.ButtonStyle.secondary,
            row=0
        )
        prev_button.callback = self.prev_day_callback
        self.add_item(prev_button)
        
        day_display_button = discord.ui.Button(
            label=f"{current_date_info['day_name']}, {current_date_info['date']}",
            style=discord.ButtonStyle.primary,
            disabled=True,
            row=0
        )
        self.add_item(day_display_button)
        
        next_button = discord.ui.Button(
            label="Next Day ▶",
            style=discord.ButtonStyle.secondary, 
            row=0
        )
        next_button.callback = self.next_day_callback
        self.add_item(next_button)
        
        # Row 1 & 2: Time slots (3-4 per row)
        time_slots = ['6PM', '7PM', '8PM', '9PM', '10PM', '11PM', '12AM']
        time_values = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']
        
        for i, (time_label, time_value) in enumerate(zip(time_slots, time_values)):
            # Determine button style
            is_selected = self.schedule_state[current_day_name].get(time_value, False)
            day_status = self.schedule_state[current_day_name].get('status')
            
            if day_status == 'all_day':
                style = discord.ButtonStyle.green
            elif day_status == 'not_available':
                style = discord.ButtonStyle.red
            elif day_status == 'unsure':
                style = discord.ButtonStyle.secondary
            elif is_selected:
                style = discord.ButtonStyle.green
            else:
                style = discord.ButtonStyle.gray
            
            row = 1 if i < 4 else 2  # First 4 in row 1, rest in row 2
            
            time_button = TimeSlotButton(
                label=time_label,
                time_value=time_value,
                day_name=current_day_name,
                style=style,
                row=row
            )
            self.add_item(time_button)
        
        # Row 3: Day action buttons
        all_day_button = DayActionButton(
            label="All Day Available",
            action="all_day",
            style=discord.ButtonStyle.blurple,
            row=3
        )
        self.add_item(all_day_button)
        
        not_available_button = DayActionButton(
            label="Not Available",
            action="not_available",
            style=discord.ButtonStyle.red,
            row=3
        )
        self.add_item(not_available_button)
        
        unsure_button = DayActionButton(
            label="Unsure",
            action="unsure",
            style=discord.ButtonStyle.secondary,
            row=3
        )
        self.add_item(unsure_button)
        
        # Row 4: Finalize button
        finalize_button = discord.ui.Button(
            label="✅ Finalize Schedule",
            style=discord.ButtonStyle.green,
            row=4
        )
        finalize_button.callback = self.finalize_schedule_callback
        self.add_item(finalize_button)
    
    async def update_view(self, interaction: discord.Interaction):
        """Update the view with new buttons and embed content"""
        self.clear_items()
        self.create_calendar_buttons()
        
        # Update embed
        embed = interaction.message.embeds[0]
        embed.title = f"📅 Editing: {self.session.schedule_dates[self.current_day_index]['full_date']}"
        
        # Update progress
        days_completed = 0
        status_text = ""
        for day_name, state in self.schedule_state.items():
            date_info = self.session.get_date_info(day_name)
            day_display = f"{date_info['day_name']}, {date_info['date']}"
            
            if state.get('status') == 'not_available':
                status_text += f"**{day_display}:** ❌ Not available\n"
                days_completed += 1
            elif state.get('status') == 'all_day':
                status_text += f"**{day_display}:** ✅ All day\n"
                days_completed += 1
            elif state.get('status') == 'unsure':
                status_text += f"**{day_display}:** ❓ Unsure\n"
                days_completed += 1
            elif state.get('status') == 'partial':
                times_count = sum(1 for t, s in state.items() if s and t != 'status')
                status_text += f"**{day_display}:** ✅ {times_count} time slots\n"
                days_completed += 1
            else:
                status_text += f"**{day_display}:** ⏳ Not set\n"
        
        # Update the progress field
        embed.set_field_at(
            0, 
            name=f"📋 Progress: {days_completed}/7 days completed",
            value=status_text,
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def prev_day_callback(self, interaction: discord.Interaction):
        self.current_day_index = (self.current_day_index - 1) % 7
        await self.update_view(interaction)
        
    async def next_day_callback(self, interaction: discord.Interaction):
        self.current_day_index = (self.current_day_index + 1) % 7
        await self.update_view(interaction)
        
    async def finalize_schedule_callback(self, interaction: discord.Interaction):
        try:
            # Convert internal state to the format expected by the session object
            final_schedule = {}
            days_completed = 0
            
            for day_name, state in self.schedule_state.items():
                if state.get('status') is not None:
                    days_completed += 1
                    
                    if state.get('status') == 'not_available' or state.get('status') == 'unsure':
                        final_schedule[day_name] = []
                    elif state.get('status') == 'all_day':
                        final_schedule[day_name] = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']
                    elif state.get('status') == 'partial':
                        final_schedule[day_name] = [time for time, selected in state.items() if selected and time != 'status']
            
            if days_completed < 7:
                await interaction.response.send_message(f"Please set all 7 days before finalizing! You have {days_completed}/7 days set.", ephemeral=True)
                return
            
            # Save to session object
            self.session.player_schedules[str(self.user_id)] = final_schedule
            if str(self.user_id) not in self.session.players_responded:
                self.session.players_responded.append(str(self.user_id))
            
            self.session = save_session(self.session)
            
            # Find cog and finalize
            draft_cog = None
            for cog in interaction.client.cogs.values():
                if hasattr(cog, 'active_sessions') and int(self.session.channel_id) in cog.active_sessions:
                    draft_cog = cog
                    break
            
            if draft_cog:
                channel = draft_cog.bot.get_channel(int(self.session.channel_id))
                remaining = self.session.expected_players - len(self.session.players_responded)
                
                if remaining > 0:
                    await channel.send(f"📝 {interaction.user.display_name} finalized their schedule. Waiting for {remaining} more players...")
                
                await interaction.response.edit_message(
                    content="✅ **Schedule finalized!** Thank you for submitting your availability.",
                    embed=None,
                    view=None
                )
                
                if self.session.is_complete():
                    await draft_cog.finalize_scheduling(channel, self.session)
            else:
                await interaction.response.send_message("Error finding scheduling session", ephemeral=True)
                
        except Exception as e:
            print(f"Error in finalize_schedule_callback: {e}")
            try:
                await interaction.response.send_message("Error finalizing schedule", ephemeral=True)
            except:
                pass

class TimeSlotButton(discord.ui.Button):
    def __init__(self, label, time_value, day_name, style, row):
        super().__init__(label=label, style=style, row=row)
        self.time_value = time_value
        self.day_name = day_name
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        state = view.schedule_state[self.day_name]
        
        # Toggle selection
        state[self.time_value] = not state.get(self.time_value, False)
        state['status'] = 'partial'  # Mark as partially set
        
        await view.update_view(interaction)

class DayActionButton(discord.ui.Button):
    def __init__(self, label, action, style, row):
        super().__init__(label=label, style=style, row=row)
        self.action = action
        
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        day_name = view.session.schedule_dates[view.current_day_index]['day_name']
        
        if self.action == "all_day":
            view.schedule_state[day_name]['status'] = 'all_day'
        elif self.action == "not_available":
            view.schedule_state[day_name]['status'] = 'not_available'
        elif self.action == "unsure":
            view.schedule_state[day_name]['status'] = 'unsure'
            
        await view.update_view(interaction)

def setup(bot):
    bot.add_cog(DraftLotteryCog(bot))