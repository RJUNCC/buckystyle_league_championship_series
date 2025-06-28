# cogs/draft_prob.py
import discord
from discord.ext import commands
import asyncio
import random
from collections import defaultdict
from typing import Dict, List, Tuple, NamedTuple
from datetime import datetime

class Player(NamedTuple):
    name: str
    tier: int

class DraftResult(NamedTuple):
    draft_order: List[Tuple[int, str, int]]
    eliminated: List[Tuple[str, int]]

class SchedulingSession:
    def __init__(self, channel_id, teams):
        self.channel_id = channel_id
        self.teams = teams
        self.player_schedules = {}
        self.players_responded = set()
        self.expected_players = 6
        self.weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        self.confirmation_message = None
        self.confirmations = {}  # {user_id: True/False}
        
    def add_player_schedule(self, user_id, schedule):
        self.player_schedules[user_id] = schedule
        self.players_responded.add(user_id)
        
    def reset_player_schedule(self, user_id):
        if user_id in self.player_schedules:
            del self.player_schedules[user_id]
        if user_id in self.players_responded:
            self.players_responded.remove(user_id)
        
    def is_complete(self):
        return len(self.players_responded) >= self.expected_players
        
    def find_common_times(self):
        if not self.player_schedules:
            return None
            
        common_times = defaultdict(list)
        
        for day in self.weekdays:
            day_schedules = []
            for user_id, schedule in self.player_schedules.items():
                if day in schedule:
                    day_schedules.append(set(schedule[day]))
            
            if len(day_schedules) >= self.expected_players:
                if day_schedules:
                    common_slots = set.intersection(*day_schedules[:self.expected_players])
                    if common_slots:
                        common_times[day] = sorted(list(common_slots))
        
        return dict(common_times) if common_times else None

class TimeSelectionView(discord.ui.View):
    def __init__(self, user_id, day, session):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.day = day
        self.session = session
        self.selected_times = set()
        
    @discord.ui.select(
        placeholder="Select available times (you can select multiple)",
        options=[
            discord.SelectOption(label="12:00 PM", value="12:00"),
            discord.SelectOption(label="12:30 PM", value="12:30"),
            discord.SelectOption(label="1:00 PM", value="13:00"),
            discord.SelectOption(label="1:30 PM", value="13:30"),
            discord.SelectOption(label="2:00 PM", value="14:00"),
            discord.SelectOption(label="2:30 PM", value="14:30"),
            discord.SelectOption(label="3:00 PM", value="15:00"),
            discord.SelectOption(label="3:30 PM", value="15:30"),
            discord.SelectOption(label="4:00 PM", value="16:00"),
            discord.SelectOption(label="4:30 PM", value="16:30"),
            discord.SelectOption(label="5:00 PM", value="17:00"),
            discord.SelectOption(label="5:30 PM", value="17:30"),
            discord.SelectOption(label="6:00 PM", value="18:00"),
            discord.SelectOption(label="6:30 PM", value="18:30"),
            discord.SelectOption(label="7:00 PM", value="19:00"),
            discord.SelectOption(label="7:30 PM", value="19:30"),
            discord.SelectOption(label="8:00 PM", value="20:00"),
            discord.SelectOption(label="8:30 PM", value="20:30"),
            discord.SelectOption(label="9:00 PM", value="21:00"),
            discord.SelectOption(label="9:30 PM", value="21:30"),
            discord.SelectOption(label="10:00 PM", value="22:00"),
            discord.SelectOption(label="10:30 PM", value="22:30"),
            discord.SelectOption(label="11:00 PM", value="23:00"),
            discord.SelectOption(label="11:30 PM", value="23:30"),
            discord.SelectOption(label="12:00 AM", value="00:00"),
        ],
        max_values=25,
        min_values=0
    )
    async def time_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        self.selected_times = set(select.values)
        
        if self.selected_times:
            times_display = ", ".join([self.format_time_display(t) for t in sorted(self.selected_times)])
            await interaction.response.edit_message(
                content=f"**{self.day}** - Selected times: {times_display}\n\nClick 'Confirm' to save these times or select different ones.",
                view=self
            )
        else:
            await interaction.response.edit_message(
                content=f"**{self.day}** - No times selected (not available)\n\nClick 'Confirm' to save or select times above.",
                view=self
            )
    
    def format_time_display(self, time_24h):
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
    
    @discord.ui.button(label="Confirm Times", style=discord.ButtonStyle.green)
    async def confirm_times(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        # Save the times for this day
        if self.user_id not in self.session.player_schedules:
            self.session.player_schedules[self.user_id] = {}
            
        self.session.player_schedules[self.user_id][self.day] = list(self.selected_times)
        
        await interaction.response.edit_message(
            content=f"✅ **{self.day}** times saved! Use `/my_schedule` again to set other days or check your full schedule.",
            view=None
        )
    
    @discord.ui.button(label="Not Available", style=discord.ButtonStyle.red)
    async def not_available(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        if self.user_id not in self.session.player_schedules:
            self.session.player_schedules[self.user_id] = {}
            
        self.session.player_schedules[self.user_id][self.day] = []
        
        await interaction.response.edit_message(
            content=f"✅ **{self.day}** marked as not available! Use `/my_schedule` again to set other days.",
            view=None
        )
    
    @discord.ui.button(label="Available All Day", style=discord.ButtonStyle.blurple)
    async def all_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        # Set all available times
        all_times = []
        for hour in range(12, 24):
            all_times.extend([f"{hour:02d}:00", f"{hour:02d}:30"])
        for hour in range(0, 1):  # Just midnight
            all_times.extend([f"{hour:02d}:00"])
            
        if self.user_id not in self.session.player_schedules:
            self.session.player_schedules[self.user_id] = {}
            
        self.session.player_schedules[self.user_id][self.day] = all_times
        
        await interaction.response.edit_message(
            content=f"✅ **{self.day}** set to all day available (12 PM - 12 AM)! Use `/my_schedule` again to set other days.",
            view=None
        )

class DaySelectionView(discord.ui.View):
    def __init__(self, user_id, session):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.session = session
        
    @discord.ui.select(
        placeholder="Select a day to set your availability",
        options=[
            discord.SelectOption(label="Monday", value="Monday", emoji="📅"),
            discord.SelectOption(label="Tuesday", value="Tuesday", emoji="📅"),
            discord.SelectOption(label="Wednesday", value="Wednesday", emoji="📅"),
            discord.SelectOption(label="Thursday", value="Thursday", emoji="📅"),
            discord.SelectOption(label="Friday", value="Friday", emoji="📅"),
            discord.SelectOption(label="Saturday", value="Saturday", emoji="📅"),
            discord.SelectOption(label="Sunday", value="Sunday", emoji="📅"),
        ]
    )
    async def day_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        selected_day = select.values[0]
        time_view = TimeSelectionView(self.user_id, selected_day, self.session)
        
        await interaction.response.edit_message(
            content=f"Setting availability for **{selected_day}**\nSelect all times you're available to play:",
            view=time_view
        )
    
    @discord.ui.button(label="View My Schedule", style=discord.ButtonStyle.secondary)
    async def view_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        if self.user_id not in self.session.player_schedules:
            await interaction.response.send_message("You haven't set any times yet!", ephemeral=True)
            return
            
        schedule = self.session.player_schedules[self.user_id]
        schedule_text = "**Your Current Schedule:**\n"
        
        days_set = 0
        for day in self.session.weekdays:
            if day in schedule:
                days_set += 1
                if not schedule[day]:
                    schedule_text += f"**{day}:** Not available\n"
                elif len(schedule[day]) >= 20:
                    schedule_text += f"**{day}:** All day available\n"
                else:
                    times = [self.format_time_display(t) for t in sorted(schedule[day])]
                    schedule_text += f"**{day}:** {', '.join(times)}\n"
            else:
                schedule_text += f"**{day}:** Not set\n"
        
        schedule_text += f"\n**Progress:** {days_set}/7 days completed"
        
        if days_set == 7:
            schedule_text += "\n✅ **Ready to finalize!** Use the 'Finalize Schedule' button."
            
        await interaction.response.send_message(schedule_text, ephemeral=True)
    
    def format_time_display(self, time_24h):
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
    
    @discord.ui.button(label="Finalize Schedule", style=discord.ButtonStyle.green)
    async def finalize_schedule(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        if self.user_id not in self.session.player_schedules:
            await interaction.response.send_message("You haven't set any times yet!", ephemeral=True)
            return
        
        schedule = self.session.player_schedules[self.user_id]
        days_set = len(schedule)
        
        if days_set < 7:
            await interaction.response.send_message(f"Please set all 7 days before finalizing! You have {days_set}/7 days set.", ephemeral=True)
            return
        
        # Add user to responded list
        self.session.players_responded.add(self.user_id)
        
        # Find the cog to access bot and finalize_scheduling method
        draft_cog = None
        for cog in interaction.client.cogs.values():
            if hasattr(cog, 'active_sessions') and self.session.channel_id in cog.active_sessions:
                draft_cog = cog
                break
        
        if draft_cog:
            channel = draft_cog.bot.get_channel(self.session.channel_id)
            remaining = self.session.expected_players - len(self.session.players_responded)
            
            if remaining > 0:
                await channel.send(f"📝 {interaction.user.display_name} finalized their schedule. Waiting for {remaining} more players...")
            
            await interaction.response.edit_message(
                content="✅ **Schedule finalized!** Thank you for submitting your availability.",
                view=None
            )
            
            # Check if all schedules are complete
            if self.session.is_complete():
                await draft_cog.finalize_scheduling(channel, self.session)

class ConfirmationView(discord.ui.View):
    def __init__(self, session, game_time_info, cog):
        super().__init__(timeout=600)  # 10 minute timeout
        self.session = session
        self.game_time_info = game_time_info
        self.cog = cog
        
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        # Check if user is part of this game
        if user_id not in self.session.player_schedules:
            await interaction.response.send_message("You're not part of this scheduled game!", ephemeral=True)
            return
            
        self.session.confirmations[user_id] = True
        confirmed = sum(1 for c in self.session.confirmations.values() if c)
        total = len(self.session.player_schedules)
        
        await interaction.response.send_message(f"✅ You confirmed the game time! ({confirmed}/{total} confirmed)", ephemeral=True)
        
        # Check if everyone confirmed
        if confirmed >= self.session.expected_players:
            channel = self.cog.bot.get_channel(self.session.channel_id)
            final_embed = discord.Embed(
                title="🎮 Game Confirmed!",
                description=f"**{self.game_time_info['day']} at {self.game_time_info['time']}**",
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
    
    @discord.ui.button(label="❌ Can't Make It", style=discord.ButtonStyle.red)
    async def decline_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        if user_id not in self.session.player_schedules:
            await interaction.response.send_message("You're not part of this scheduled game!", ephemeral=True)
            return
            
        self.session.confirmations[user_id] = False
        
        await interaction.response.send_message(
            "❌ You declined the game time. Please update your schedule using `/my_schedule` and set more accurate times.",
            ephemeral=True
        )
        
        # Reset this player's status so they can resubmit
        self.session.reset_player_schedule(user_id)
        
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
        self.active_sessions = {}  # Store active scheduling sessions

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
                # For eliminated players, we need to calculate their probability of NOT being picked in any of the 8 positions
                # This is complex, so we'll use the base weight for position 9 (elimination)
                base_weights = self.lottery.weights[player_tier]
                if len(base_weights) > 8:
                    return base_weights[8]  # Position 9 weight
                else:
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
                "YNs",
                "Team 2", 
                "Mulignans",
                "16 Keycaps",
                "Team 5",
                "Mounties",
                "Team 7",
                "Ice Truck Killers"
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
            
            # Transition to matchups
            await asyncio.sleep(2)
            embed = discord.Embed(
                title="🔥 FIRST ROUND MATCHUPS 🔥",
                description="Time to see who faces who in the opening round!",
                color=0xff0000
            )
            embed.add_field(
                name="🏆 FINAL SEEDINGS",
                value=seeding_text,
                inline=False
            )
            await ctx.edit(embed=embed)
            await asyncio.sleep(3)
            
            # Generate and announce matchups
            matchups = [
                (1, 8),
                (2, 7),
                (3, 6),
                (4, 5)
            ]
            
            matchup_names = ["QUARTERFINAL 1", "QUARTERFINAL 2", "QUARTERFINAL 3", "QUARTERFINAL 4"]
            matchup_text = ""
            
            for i, (higher_seed, lower_seed) in enumerate(matchups):
                matchup_entry = f"⚔️ **{matchup_names[i]}**\n#{higher_seed} {seeding[higher_seed]} **VS** #{lower_seed} {seeding[lower_seed]}\n\n"
                matchup_text += matchup_entry
                
                embed = discord.Embed(
                    title=f"⚔️ {matchup_names[i]} ⚔️",
                    description=f"**#{higher_seed} {seeding[higher_seed]}**\n\n**VS**\n\n**#{lower_seed} {seeding[lower_seed]}**",
                    color=0x8b0000
                )
                
                embed.add_field(
                    name="🏆 FINAL SEEDINGS",
                    value=seeding_text,
                    inline=False
                )
                
                if matchup_text:
                    embed.add_field(
                        name="🔥 MATCHUPS SO FAR",
                        value=matchup_text,
                        inline=False
                    )
                
                await ctx.edit(embed=embed)
                await asyncio.sleep(4)
            
            # Final summary
            await asyncio.sleep(2)
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
            
            final_embed.add_field(
                name="🔥 ALL QUARTERFINAL MATCHUPS",
                value=matchup_text,
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
    async def schedule_game(self, ctx, team1: str, team2: str):
        """Start a game scheduling session"""
        channel_id = ctx.channel.id
        
        # Check if there's already an active session in this channel
        if channel_id in self.active_sessions:
            await ctx.respond("There's already an active scheduling session in this channel. Use `/cancel_schedule` to cancel it first.", ephemeral=True)
            return
        
        # Create new scheduling session
        session = SchedulingSession(channel_id, [team1, team2])
        self.active_sessions[channel_id] = session
        
        embed = discord.Embed(
            title="🎮 Game Scheduling Started!",
            description=(
                f"**Scheduling game between {team1} and {team2}**\n\n"
                f"📋 **What Players Need to Do:**\n"
                f"All **6 players** (3 from each team) must use: `/my_schedule`\n\n"
                f"🕐 **Interactive System:**\n"
                f"• Select days and times using dropdown menus\n"
                f"• Times range from 12 PM to 12 AM\n"
                f"• Easy buttons for 'Not Available' and 'All Day'\n"
                f"• View and modify your schedule anytime\n\n"
                f"🎯 **Process:**\n"
                f"1️⃣ All 6 players set their weekly availability\n"
                f"2️⃣ Bot finds common times and proposes game time\n"
                f"3️⃣ All players confirm with ✅/❌ buttons\n"
                f"4️⃣ If anyone declines, they update schedule and repeat\n\n"
                f"⏳ **Progress:** Waiting for {session.expected_players} players..."
            ),
            color=0x00ff00
        )
        embed.set_footer(text="Use /my_schedule to start setting your availability!")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="my_schedule", description="Set your weekly availability using interactive menus")
    async def my_schedule(self, ctx):
        """Interactive schedule setting"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel. Start one with `/schedule_game Team1 Team2`", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        user_id = ctx.author.id
        
        # Create the interactive view with dropdowns and buttons
        view = DaySelectionView(user_id, session)
        
        # Allow players to reset/modify their schedule
        if user_id in session.players_responded:
            embed = discord.Embed(
                title="🔄 Update Your Schedule",
                description="Use the dropdown below to select a day and set your availability. You can modify any day multiple times.",
                color=0xffa500
            )
        else:
            embed = discord.Embed(
                title="📅 Set Your Weekly Availability",
                description="Use the dropdown below to select a day and set your available times. You can modify any day multiple times.",
                color=0x0099ff
            )
        
        try:
            # Send the interactive interface directly in DM
            await ctx.author.send(embed=embed, view=view)
            await ctx.respond(f"{ctx.author.mention}, check your DMs for the interactive schedule interface!", ephemeral=True)
        except discord.Forbidden:
            await ctx.respond("I couldn't send you a DM. Please enable DMs from server members and try again.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error sending DM: {str(e)}", ephemeral=True)

    async def finalize_scheduling(self, channel, session):
        """Find common times and start confirmation process"""
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
        
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            if day in common_times and common_times[day]:
                best_day = day
                # Prefer evening times (6 PM to 10 PM)
                for time in common_times[day]:
                    hour = int(time.split(':')[0])
                    if 18 <= hour <= 22:
                        best_time = time
                        break
                if not best_time:
                    best_time = common_times[day][0]
                break
        
        if not best_day or not best_time:
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
        
        game_info = {'day': best_day, 'time': display_time}
        
        embed = discord.Embed(
            title="🎮 Proposed Game Time",
            description=f"**{best_day} at {display_time}**",
            color=0xffa500
        )
        embed.add_field(
            name="⚠️ Confirmation Required",
            value="All players must confirm this time works for them using the buttons below.",
            inline=False
        )
        embed.add_field(
            name="Available Times Found",
            value=self.format_available_times_interactive(common_times),
            inline=False
        )
        
        view = ConfirmationView(session, game_info, self)
        session.confirmation_message = await channel.send("@everyone", embed=embed, view=view)

    def format_available_times_interactive(self, common_times):
        """Format available times for display"""
        formatted = []
        for day, times in common_times.items():
            if times:
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
                formatted.append(f"**{day}:** {time_str}")
        
        return "\n".join(formatted) if formatted else "No common times found"

    @discord.slash_command(name="cancel_schedule", description="Cancel the current scheduling session")
    async def cancel_schedule(self, ctx):
        """Cancel the current scheduling session"""
        channel_id = ctx.channel.id
        
        if channel_id in self.active_sessions:
            del self.active_sessions[channel_id]
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

def setup(bot):
    bot.add_cog(DraftLotteryCog(bot))