# cogs/draft_prob.py
import discord
from discord.ext import commands
import asyncio
import random
from collections import defaultdict
from typing import Dict, List, Tuple, NamedTuple
from datetime import datetime
import re

class Player(NamedTuple):
    name: str
    tier: int

class DraftResult(NamedTuple):
    draft_order: List[Tuple[int, str, int]]
    eliminated: List[Tuple[str, int]]

class SchedulingSession:
    def __init__(self, channel_id, teams):
        self.channel_id = channel_id
        self.teams = teams  # List of team names/IDs
        self.player_schedules = {}  # {user_id: {day: [time_slots]}}
        self.players_responded = set()
        self.expected_players = 6  # 3 players per team × 2 teams
        self.weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
    def add_player_schedule(self, user_id, schedule):
        self.player_schedules[user_id] = schedule
        self.players_responded.add(user_id)
        
    def is_complete(self):
        return len(self.players_responded) >= self.expected_players
        
    def find_common_times(self):
        if not self.player_schedules:
            return None
            
        common_times = defaultdict(list)
        
        # For each day of the week
        for day in self.weekdays:
            # Get all time slots for this day from all players
            day_schedules = []
            for user_id, schedule in self.player_schedules.items():
                if day in schedule:
                    day_schedules.append(set(schedule[day]))
            
            if len(day_schedules) >= self.expected_players:
                # Find intersection of all players' available times
                if day_schedules:
                    common_slots = set.intersection(*day_schedules[:self.expected_players])
                    if common_slots:
                        common_times[day] = sorted(list(common_slots))
        
        return dict(common_times) if common_times else None

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

# Scheduling utility functions
def parse_time_input(time_str):
    """Parse various time formats into 24-hour format"""
    time_str = time_str.strip().lower()
    
    # Handle ranges like "2-4pm" or "14:00-16:00"
    if '-' in time_str:
        start, end = time_str.split('-', 1)
        start_time = parse_single_time(start.strip())
        end_time = parse_single_time(end.strip())
        if start_time and end_time:
            return generate_time_slots(start_time, end_time)
    
    # Handle single times
    single_time = parse_single_time(time_str)
    if single_time:
        return [single_time]
    
    return []

def parse_single_time(time_str):
    """Parse a single time string into 24-hour format"""
    time_str = time_str.strip().lower()
    
    # Handle formats like "2pm", "14:00", "2:30pm", "10:30pm", "11:59pm"
    am_pm_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)'
    military_pattern = r'(\d{1,2}):(\d{2})'
    simple_pattern = r'(\d{1,2})(am|pm)?'
    
    # Try AM/PM format first (this handles 10:30pm, 11:59pm, etc.)
    match = re.match(am_pm_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)
        
        # Handle 12-hour to 24-hour conversion
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
            
        # Validate hour and minute ranges
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # Try military time (24-hour format)
    match = re.match(military_pattern, time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    
    # Try simple number format (fallback for cases like "2pm", "14")
    match = re.match(simple_pattern, time_str)
    if match:
        hour = int(match.group(1))
        period = match.group(2)
        
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        elif not period and 1 <= hour <= 12:
            # Assume PM for afternoon hours without AM/PM
            if hour >= 8:
                hour += 12
                
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"
    
    return None

def generate_time_slots(start_time, end_time):
    """Generate time slots between start and end time (now supports minutes)"""
    slots = []
    
    # Parse start and end times
    start_parts = start_time.split(':')
    end_parts = end_time.split(':')
    
    start_hour = int(start_parts[0])
    start_minute = int(start_parts[1]) if len(start_parts) > 1 else 0
    
    end_hour = int(end_parts[0])
    end_minute = int(end_parts[1]) if len(end_parts) > 1 else 0
    
    # Convert to total minutes for easier calculation
    start_total_minutes = start_hour * 60 + start_minute
    end_total_minutes = end_hour * 60 + end_minute
    
    # Handle overnight ranges (like 10:30pm-11:59pm)
    if end_total_minutes <= start_total_minutes:
        end_total_minutes += 24 * 60  # Add 24 hours
    
    # Generate 30-minute slots
    current_minutes = start_total_minutes
    while current_minutes < end_total_minutes:
        hours = (current_minutes // 60) % 24
        minutes = current_minutes % 60
        slots.append(f"{hours:02d}:{minutes:02d}")
        current_minutes += 30  # 30-minute increments
    
    return slots

def parse_schedule_message(message):
    """Parse a multi-line schedule message"""
    schedule = {}
    weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    lines = message.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if ':' not in line:
            continue
            
        day_part, time_part = line.split(':', 1)
        day = day_part.strip().lower()
        
        # Find matching weekday
        matched_day = None
        for weekday in weekdays:
            if day.startswith(weekday[:3]):  # Match first 3 letters
                matched_day = weekday.capitalize()
                break
        
        if not matched_day:
            continue
            
        time_part = time_part.strip().lower()
        
        # Check if not available
        if any(word in time_part for word in ['not available', 'none', 'n/a', 'unavailable', 'busy', 'no']):
            schedule[matched_day] = []
        # Check if all day available
        elif any(phrase in time_part for phrase in ['all day', 'anytime', 'flexible', 'any time', 'whole day', 'entire day']):
            # Generate slots from 8 AM to 11 PM for "all day"
            schedule[matched_day] = [f"{hour:02d}:00" for hour in range(8, 24)]
        else:
            # Parse time slots
            time_slots = []
            # Split by commas for multiple time ranges
            time_ranges = [t.strip() for t in time_part.split(',')]
            
            for time_range in time_ranges:
                slots = parse_time_input(time_range)
                time_slots.extend(slots)
            
            schedule[matched_day] = time_slots
    
    return schedule if schedule else None

def format_available_times(common_times):
    """Format the available times for display"""
    formatted = []
    for day, times in common_times.items():
        if times:
            time_str = ", ".join(times)
            formatted.append(f"**{day}:** {time_str}")
    
    return "\n".join(formatted) if formatted else "No common times found"

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
            await ctx.respond("There's already an active scheduling session in this channel. Please wait for it to complete.", ephemeral=True)
            return
        
        # Create new scheduling session
        session = SchedulingSession(channel_id, [team1, team2])
        self.active_sessions[channel_id] = session
        
        # Main announcement embed
        main_embed = discord.Embed(
            title="🎮 Game Scheduling Started!",
            description=f"Scheduling game between **{team1}** and **{team2}**",
            color=0x00ff00
        )
        main_embed.add_field(
            name="📋 What Players Need to Do",
            value=(
                "**ALL 6 PLAYERS** (3 from each team) must submit their weekly availability using:\n"
                "```/my_schedule```"
            ),
            inline=False
        )
        main_embed.add_field(
            name="Progress",
            value=f"⏳ Waiting for {session.expected_players} players to respond...",
            inline=False
        )
        
        # Detailed instructions embed
        instructions_embed = discord.Embed(
            title="📝 How to Submit Your Schedule",
            description="When you use `/my_schedule`, the bot will DM you for your availability. Here's how to format it:",
            color=0x0099ff
        )
        
        instructions_embed.add_field(
            name="🕐 Time Formats Accepted",
            value=(
                "• **Single times:** `2pm`, `7pm`, `14:00`, `20:30`\n"
                "• **Time ranges:** `2pm-6pm`, `14:00-18:00`\n"
                "• **Multiple slots:** `2pm-4pm, 7pm-9pm`\n"
                "• **All day available:** `all day`, `anytime`, `flexible`\n"
                "• **Not available:** `not available`, `none`, `n/a`, `busy`"
            ),
            inline=False
        )
        
        instructions_embed.add_field(
            name="📝 Alternative Method (If DMs Don't Work)",
            value=(
                "If `/my_schedule` doesn't send you a DM, use this instead:\n"
                "```/schedule_submit schedule:\n"
                "Monday: 2pm-6pm, 8pm-10pm\n"
                "Tuesday: All day\n"
                "Wednesday: Not available\n"
                "Thursday: 7pm-11pm\n"
                "Friday: Anytime\n"
                "Saturday: 12pm-3pm, 6pm-9pm\n"
                "Sunday: None```"
            ),
            inline=False
        )
        
        instructions_embed.add_field(
            name="⚠️ Important Notes",
            value=(
                "• You have **5 minutes** to respond in DMs after using `/my_schedule`\n"
                "• Make sure your DMs are open to receive the bot's message\n"
                "• Include ALL 7 days of the week in your response\n"
                "• The bot will find times that work for ALL 6 players"
            ),
            inline=False
        )
        
        instructions_embed.add_field(
            name="🎯 What Happens Next",
            value=(
                "1️⃣ All 6 players submit schedules\n"
                "2️⃣ Bot finds common available times\n"
                "3️⃣ Bot announces best game time with @everyone\n"
                "4️⃣ Players confirm and get ready to play!"
            ),
            inline=False
        )
        
        await ctx.respond(embed=main_embed)
        await ctx.followup.send(embed=instructions_embed)

    @discord.slash_command(name="my_schedule", description="Submit your weekly schedule for the current game")
    async def my_schedule(self, ctx):
        """Allow players to input their weekly schedule"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel. Start one with `/schedule_game Team1 Team2`", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        user_id = ctx.author.id
        
        if user_id in session.players_responded:
            await ctx.respond("You've already submitted your schedule for this game!", ephemeral=True)
            return
        
        # Try to create DM to collect schedule privately
        dm_success = False
        dm_channel = None
        
        try:
            dm_channel = await ctx.author.create_dm()
            
            embed = discord.Embed(
                title="📅 Weekly Schedule Input",
                description="Please provide your availability for each day of the week.",
                color=0x0099ff
            )
            embed.add_field(
                name="🕐 Time Format Options",
                value=(
                    "• **Single times:** `2pm`, `7pm`, `14:00`, `20:30`\n"
                    "• **Time ranges:** `2pm-6pm`, `14:00-18:00`\n"
                    "• **Multiple slots:** `2pm-4pm, 7pm-9pm`\n"
                    "• **All day available:** `all day`, `anytime`, `flexible`\n"
                    "• **Not available:** `not available`, `none`, `n/a`, `busy`"
                ),
                inline=False
            )
            embed.add_field(
                name="📝 Required Format",
                value=(
                    "Reply with ALL 7 days in this format:\n\n"
                    "```Monday: 2pm-6pm, 8pm-10pm\n"
                    "Tuesday: All day\n"
                    "Wednesday: Not available\n"
                    "Thursday: 7pm-11pm\n"
                    "Friday: Anytime\n"
                    "Saturday: 12pm-3pm, 6pm-9pm\n"
                    "Sunday: None```"
                ),
                inline=False
            )
            embed.add_field(
                name="⏰ Time Limit",
                value="You have **5 minutes** to respond with your complete schedule!",
                inline=False
            )
            
            await dm_channel.send(embed=embed)
            dm_success = True
            await ctx.respond(f"✅ {ctx.author.mention}, I've sent you a DM! Please check your direct messages to input your schedule.", ephemeral=True)
            
        except discord.Forbidden:
            # DM failed, use channel method instead
            await ctx.respond(
                f"❌ I couldn't send you a DM, {ctx.author.mention}. Your DMs might be disabled.\n"
                f"I'll send you an ephemeral message instead. Please respond with your schedule in the format shown below:",
                ephemeral=True
            )
            
            # Send ephemeral instructions
            embed = discord.Embed(
                title="📅 Weekly Schedule Input (Ephemeral)",
                description="Since DMs are disabled, please use `/schedule_submit` with your schedule.",
                color=0xff9900
            )
            embed.add_field(
                name="🕐 Time Format Options",
                value=(
                    "• **Single times:** `2pm`, `7pm`, `14:00`, `20:30`\n"
                    "• **Time ranges:** `2pm-6pm`, `14:00-18:00`\n"
                    "• **Multiple slots:** `2pm-4pm, 7pm-9pm`\n"
                    "• **All day available:** `all day`, `anytime`, `flexible`\n"
                    "• **Not available:** `not available`, `none`, `n/a`, `busy`"
                ),
                inline=False
            )
            embed.add_field(
                name="📝 Use This Command Format",
                value=(
                    "```/schedule_submit schedule:\n"
                    "Monday: 2pm-6pm, 8pm-10pm\n"
                    "Tuesday: All day\n"
                    "Wednesday: Not available\n"
                    "Thursday: 7pm-11pm\n"
                    "Friday: Anytime\n"
                    "Saturday: 12pm-3pm, 6pm-9pm\n"
                    "Sunday: None```"
                ),
                inline=False
            )
            
            await ctx.followup.send(embed=embed, ephemeral=True)
            return
        
        except Exception as e:
            await ctx.respond(f"❌ Error creating DM: {str(e)}. Please try again or contact an admin.", ephemeral=True)
            return
        
        if dm_success and dm_channel:
            # Wait for DM response
            def check_dm(message):
                return (message.author == ctx.author and 
                       isinstance(message.channel, discord.DMChannel))
            
            try:
                response = await self.bot.wait_for('message', check=check_dm, timeout=300.0)
                schedule = parse_schedule_message(response.content)
                
                if schedule:
                    session.add_player_schedule(user_id, schedule)
                    
                    # Show confirmation with parsed schedule
                    confirmation_embed = discord.Embed(
                        title="✅ Schedule Received!",
                        description="Here's what I understood from your schedule:",
                        color=0x00ff00
                    )
                    
                    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        if day in schedule:
                            if not schedule[day]:
                                availability = "Not available"
                            elif len(schedule[day]) >= 15:  # All day has many slots
                                availability = "All day (8 AM - 11 PM)"
                            else:
                                availability = ", ".join(schedule[day])
                            confirmation_embed.add_field(name=day, value=availability, inline=True)
                    
                    await dm_channel.send(embed=confirmation_embed)
                    
                    # Update progress in main channel
                    remaining = session.expected_players - len(session.players_responded)
                    if remaining > 0:
                        await ctx.channel.send(f"📝 {ctx.author.display_name} submitted their schedule. Waiting for {remaining} more players...")
                    
                    # Check if we have all schedules
                    if session.is_complete():
                        await self.finalize_scheduling(ctx.channel, session)
                        
                else:
                    await dm_channel.send("❌ Could not parse your schedule. Please try again with the correct format.")
                    
            except asyncio.TimeoutError:
                try:
                    await dm_channel.send("⏰ Schedule input timed out. Please use `/my_schedule` again to retry.")
                except:
                    pass  # DM might be closed

    @discord.slash_command(name="schedule_submit", description="Submit your schedule directly (fallback if DMs don't work)")
    async def schedule_submit(self, ctx, schedule: str):
        """Fallback method to submit schedule if DMs don't work"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel. Start one with `/schedule_game Team1 Team2`", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        user_id = ctx.author.id
        
        if user_id in session.players_responded:
            await ctx.respond("You've already submitted your schedule for this game! Use `/schedule_update` to change it.", ephemeral=True)
            return
        
        # Parse the schedule
        parsed_schedule = parse_schedule_message(schedule)
        
        if parsed_schedule:
            session.add_player_schedule(user_id, parsed_schedule)
            
            # Show confirmation with parsed schedule (ephemeral)
            confirmation_embed = discord.Embed(
                title="✅ Schedule Received!",
                description="Here's what I understood from your schedule:",
                color=0x00ff00
            )
            
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                if day in parsed_schedule:
                    if not parsed_schedule[day]:
                        availability = "Not available"
                    elif len(parsed_schedule[day]) >= 15:  # All day has many slots
                        availability = "All day (8 AM - 11 PM)"
                    else:
                        availability = ", ".join(parsed_schedule[day])
                    confirmation_embed.add_field(name=day, value=availability, inline=True)
            
            await ctx.respond(embed=confirmation_embed, ephemeral=True)
            
            # Update progress in main channel
            remaining = session.expected_players - len(session.players_responded)
            if remaining > 0:
                await ctx.channel.send(f"📝 {ctx.author.display_name} submitted their schedule. Waiting for {remaining} more players...")
            
            # Check if we have all schedules
            if session.is_complete():
                await self.finalize_scheduling(ctx.channel, session)
                
        else:
            await ctx.respond("❌ Could not parse your schedule. Please check the format and try again.", ephemeral=True)

    @discord.slash_command(name="schedule_update", description="Update your already submitted schedule")
    async def schedule_update(self, ctx, schedule: str):
        """Allow users to update their submitted schedule"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel. Start one with `/schedule_game Team1 Team2`", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        user_id = ctx.author.id
        
        if user_id not in session.players_responded:
            await ctx.respond("You haven't submitted a schedule yet! Use `/my_schedule` or `/schedule_submit` first.", ephemeral=True)
            return
        
        # Parse the new schedule
        parsed_schedule = parse_schedule_message(schedule)
        
        if parsed_schedule:
            # Update the existing schedule
            session.player_schedules[user_id] = parsed_schedule
            
            # Show confirmation with updated schedule (ephemeral)
            confirmation_embed = discord.Embed(
                title="✅ Schedule Updated!",
                description="Here's your updated schedule:",
                color=0x00ff00
            )
            
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                if day in parsed_schedule:
                    if not parsed_schedule[day]:
                        availability = "Not available"
                    elif len(parsed_schedule[day]) >= 15:  # All day has many slots
                        availability = "All day (8 AM - 11 PM)"
                    else:
                        availability = ", ".join(parsed_schedule[day])
                    confirmation_embed.add_field(name=day, value=availability, inline=True)
            
            await ctx.respond(embed=confirmation_embed, ephemeral=True)
            
            # Notify channel that someone updated their schedule
            await ctx.channel.send(f"📝 {ctx.author.display_name} updated their schedule.")
            
            # Check if we have all schedules and can finalize
            if session.is_complete():
                await self.finalize_scheduling(ctx.channel, session)
                
        else:
            await ctx.respond("❌ Could not parse your schedule. Please check the format and try again.", ephemeral=True)

    @discord.slash_command(name="schedule_view", description="View your current submitted schedule")
    async def schedule_view(self, ctx):
        """Allow users to view their current submitted schedule"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        user_id = ctx.author.id
        
        if user_id not in session.players_responded:
            await ctx.respond("You haven't submitted a schedule yet! Use `/my_schedule` or `/schedule_submit` first.", ephemeral=True)
            return
        
        user_schedule = session.player_schedules[user_id]
        
        # Show current schedule
        view_embed = discord.Embed(
            title="👀 Your Current Schedule",
            description="Here's what you submitted:",
            color=0x0099ff
        )
        
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            if day in user_schedule:
                if not user_schedule[day]:
                    availability = "Not available"
                elif len(user_schedule[day]) >= 15:  # All day has many slots
                    availability = "All day (8 AM - 11 PM)"
                else:
                    availability = ", ".join(user_schedule[day])
                view_embed.add_field(name=day, value=availability, inline=True)
        
        view_embed.add_field(
            name="💡 Want to Change It?",
            value="Use `/schedule_update` with your new schedule!",
            inline=False
        )
        
        await ctx.respond(embed=view_embed, ephemeral=True)

    async def finalize_scheduling(self, channel, session):
        """Find common times and announce the game time"""
        common_times = session.find_common_times()
        
        if not common_times:
            embed = discord.Embed(
                title="❌ No Common Times Found",
                description="Unfortunately, no times work for all players.",
                color=0xff0000
            )
            embed.add_field(
                name="Suggestion",
                value="Players may need to adjust their schedules or consider alternative arrangements.",
                inline=False
            )
            await channel.send(embed=embed)
        else:
            # Pick the best time (earliest day with most options)
            best_day = None
            best_times = None
            
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                if day in common_times and common_times[day]:
                    best_day = day
                    best_times = common_times[day]
                    break
            
            if best_day and best_times:
                # Pick a reasonable time (prefer evening hours)
                game_time = best_times[0]
                for time in best_times:
                    hour = int(time.split(':')[0])
                    if 18 <= hour <= 21:  # 6 PM to 9 PM preferred
                        game_time = time
                        break
                
                embed = discord.Embed(
                    title="🎉 Game Time Scheduled!",
                    description=f"**{best_day} at {game_time}**",
                    color=0x00ff00
                )
                embed.add_field(
                    name="All Available Times",
                    value=format_available_times(common_times),
                    inline=False
                )
                embed.add_field(
                    name="Next Steps",
                    value="Please confirm this time works and be ready to play!",
                    inline=False
                )
                
                await channel.send("@everyone")
                await channel.send(embed=embed)
        
        # Clean up session
        del self.active_sessions[session.channel_id]

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
            value=f"{len(session.players_responded)}/{session.expected_players} players responded",
            inline=False
        )
        embed.add_field(
            name="Remaining",
            value=f"Waiting for {remaining} more players",
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