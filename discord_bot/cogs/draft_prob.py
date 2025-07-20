# cogs/draft_prob.py
import discord
import json
from discord.ext import commands, tasks
import asyncio
import random
from collections import defaultdict
from typing import Dict, List, Tuple, NamedTuple
from datetime import datetime, timedelta
import discord.utils

# Import database functions
try:
    from models.scheduling import save_session, delete_session, get_all_active_sessions, load_session, SchedulingSession as DBSchedulingSession
except ImportError as e:
    print(f"CRITICAL: Failed to import scheduling module: {e}")
    import traceback
    traceback.print_exc()
    # Make it obvious that persistence is disabled
    save_session = lambda x: print("DATABASE DISABLED: save_session called")
    load_session = lambda x: print("DATABASE DISABLED: load_session called")
    delete_session = lambda x: print("DATABASE DISABLED: delete_session called")
    get_all_active_sessions = lambda: []
    # Define a dummy class to avoid NameError
    class DBSchedulingSession:
        pass

class Player(NamedTuple):
    name: str
    tier: int

class DraftResult(NamedTuple):
    draft_order: List[Tuple[int, str, int]]
    eliminated: List[Tuple[str, int]]


class AskPlayerView(discord.ui.View):
    def __init__(self, session, game_time_info, cog):
        super().__init__(timeout=86400) # 24-hour timeout for the player to respond
        self.session = session
        self.game_time_info = game_time_info
        self.cog = cog

    @discord.ui.button(label="✅ Yes, I can make it!", style=discord.ButtonStyle.green)
    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        self.session.confirmations[user_id] = True
        save_session(self.session)

        await interaction.response.send_message("Thanks for confirming! The other players will now be asked to confirm this time.")

        # Now, propose the time to the main channel
        channel = self.cog.bot.get_channel(int(self.session.channel_id))
        if channel:
            # This will re-trigger the confirmation process for the other 5 players
            await self.cog.finalize_scheduling(channel, self.session)

    @discord.ui.button(label="❌ No, I can't make it", style=discord.ButtonStyle.red)
    async def decline(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_message("No problem. The bot will continue searching for other possible times.")
        # The bot will automatically try the next 5/6 time when finalize_scheduling is called again.
        # No need to do anything here as the previously proposed time is already logged.
        channel = self.cog.bot.get_channel(int(self.session.channel_id))
        if channel:
            await self.cog.finalize_scheduling(channel, self.session)


class ConfirmationView(discord.ui.View):
    def __init__(self, session, game_time_info, cog, message=None):
        super().__init__(timeout=600)
        self.session = session
        self.game_time_info = game_time_info
        self.cog = cog
        self.message = message

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.green)
    async def confirm_game(self, button: discord.ui.Button, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        session = load_session(self.session.channel_id)
        if not session:
            await interaction.response.send_message("Error: Could not find the scheduling session.", ephemeral=True)
            return

        if user_id not in session.player_schedules:
            await interaction.response.send_message("You're not part of this scheduled game!", ephemeral=True)
            return

        session.confirmations[user_id] = True
        updated_session = save_session(session)
        if updated_session:
            self.cog.active_sessions[int(updated_session.channel_id)] = updated_session
            session = updated_session # Use the updated session for the rest of the logic

        confirmed = sum(1 for c in session.confirmations.values() if c)
        total = len(session.player_schedules)

        await interaction.response.send_message(f"✅ You confirmed the game time! ({confirmed}/{total} confirmed)", ephemeral=True)

        if self.message:
            team1_role = discord.utils.get(self.message.guild.roles, name=session.team1)
            team2_role = discord.utils.get(self.message.guild.roles, name=session.team2)
            team1_mention = f"<@&{team1_role.id}>" if team1_role else session.team1
            team2_mention = f"<@&{team2_role.id}>" if team2_role else session.team2
            await self.message.edit(content=f"{team1_mention} {team2_mention} Game Time: {self.game_time_info['full_date']} @ {self.game_time_info['time']} ({confirmed}/{total} confirmed)")

        if confirmed >= session.expected_players:
            channel = self.cog.bot.get_channel(int(session.channel_id))
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

            delete_session(session.channel_id)
            if int(session.channel_id) in self.cog.active_sessions:
                del self.cog.active_sessions[int(session.channel_id)]


    @discord.ui.button(label="❌ Can't Make It", style=discord.ButtonStyle.red)
    async def decline_game(self, button: discord.ui.Button, interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        session = load_session(self.session.channel_id)
        if not session:
            await interaction.response.send_message("Error: Could not find the scheduling session.", ephemeral=True)
            return

        if user_id not in session.player_schedules:
            await interaction.response.send_message("You're not part of this scheduled game!", ephemeral=True)
            return

        session.confirmations[user_id] = False
        updated_session = save_session(session)
        if updated_session:
            self.cog.active_sessions[int(updated_session.channel_id)] = updated_session
            session = updated_session

        await interaction.response.send_message(
            "❌ You declined the game time. The system will now attempt to find the next suitable time.",
            ephemeral=True
        )

        if self.message:
            # Update the message to reflect the decline and new search
            await self.message.edit(content=f"@everyone Game Time: {self.game_time_info['full_date']} @ {self.game_time_info['time']} (Declined by {interaction.user.display_name}) - Searching for next time...")

        channel = self.cog.bot.get_channel(int(session.channel_id))
        await channel.send(f"⚠️ {interaction.user.display_name} can't make the proposed time. Searching for the next available time...")
        
        # Automatically propose the next game time
        await self.cog.finalize_scheduling(channel, session)

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
        self.active_sessions: Dict[int, DBSchedulingSession] = {}
        self.background_task = None
        self.weekly_schedule_reminder.start()
        self.dm_unconfirmed_players.start()
    
    async def cog_load(self):
        try:
            self.background_task = asyncio.create_task(self.load_active_sessions())
            print("✅ Background task for loading sessions started")
        except Exception as e:
            print(f"Error starting background task: {e}")
    
    async def cog_unload(self):
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                print("✅ Background task cancelled successfully")
            except Exception as e:
                print(f"Error cancelling background task: {e}")
    
    async def load_active_sessions(self):
        print("DEBUG: Attempting to load active sessions from database...")
        try:
            await self.bot.wait_until_ready()
            print("DEBUG: Bot is ready, proceeding to load sessions.")
            
            active_sessions = get_all_active_sessions()
            print(f"DEBUG: Found {len(active_sessions)} active sessions in database.")

            for db_session in active_sessions:
                try:
                    self.active_sessions[int(db_session.channel_id)] = db_session
                    print(f"✅ Loaded scheduling session for channel {db_session.channel_id}")
                except Exception as e:
                    print(f"ERROR: Failed to load session from DB object for channel {db_session.channel_id}: {e}")

        except asyncio.CancelledError:
            print("📝 Session loading cancelled")
            raise
        except Exception as e:
            print(f"CRITICAL: Error loading sessions from database: {e}")
            import traceback
            traceback.print_exc()

    @tasks.loop(hours=1)
    async def weekly_schedule_reminder(self):
        now = datetime.now()
        # Sunday at 12:00 PM
        if now.weekday() == 6 and now.hour == 12:
            active_sessions = get_all_active_sessions()
            for session in active_sessions:
                # --- FIX: Update session for the new week ---
                session.schedule_dates = session.generate_next_week()  # Generate new dates
                session.proposed_times = []  # Clear old proposals
                session.confirmations = {}   # Clear old confirmations
                save_session(session)        # Save changes to the database
                # --- END FIX ---

                channel = self.bot.get_channel(int(session.channel_id))
                if channel:
                    team1_role = discord.utils.get(channel.guild.roles, name=session.team1)
                    team2_role = discord.utils.get(channel.guild.roles, name=session.team2)
                    team1_mention = f"<@&{team1_role.id}>" if team1_role else session.team1
                    team2_mention = f"<@&{team2_role.id}>" if team2_role else session.team2
                    await channel.send(f"{team1_mention} {team2_mention} it's time to schedule your game for this week! Please use `/my_schedule` to set your availability.")

    @tasks.loop(hours=4)
    async def dm_unconfirmed_players(self):
        """Periodically sends a DM reminder to players who haven't confirmed a proposed game time."""
        active_sessions = get_all_active_sessions()
        for session in active_sessions:
            if not session.proposed_times:
                continue  # Skip if no time has been proposed yet

            all_player_ids = set(session.player_schedules.keys())
            confirmed_player_ids = {uid for uid, confirmed in session.confirmations.items() if confirmed}
            unconfirmed_player_ids = all_player_ids - confirmed_player_ids

            if not unconfirmed_player_ids:
                continue # All players have confirmed

            channel = self.bot.get_channel(int(session.channel_id))
            if not channel:
                continue

            for user_id in unconfirmed_player_ids:
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    if user:
                        embed = discord.Embed(
                            title="🗓️ Game Confirmation Reminder",
                            description=f"Hi {user.display_name}! Just a friendly reminder to confirm the proposed game time for **{session.team1} vs {session.team2}** in the #{channel.name} channel.",
                            color=0xffa500
                        )
                        embed.add_field(name="Action Needed", value=f"Please go to the #{channel.name} channel to click '✅ Confirm' or '❌ Can't Make It'.")
                        await user.send(embed=embed)
                except discord.Forbidden:
                    print(f"Could not send DM to user {user_id} - DMs are likely disabled.")
                except Exception as e:
                    print(f"Error sending DM to user {user_id}: {e}")
    
    @dm_unconfirmed_players.before_loop
    async def before_dm_unconfirmed_players(self):
        await self.bot.wait_until_ready()

    def get_pick_emoji(self, pick: int) -> str:
        if pick <= 2:
            return "⭐"
        elif pick <= 4:
            return "🔥" 
        elif pick <= 6:
            return "✨"
        else:
            return "💫"

    def _add_chunked_field(self, embed, name, value, inline=False):
        if len(value) <= 1024:
            embed.add_field(name=name, value=value, inline=inline)
        else:
            chunks = [value[i:i+1000] for i in range(0, len(value), 1000)] # Leave some room for (cont.)
            for i, chunk in enumerate(chunks):
                field_name = f"{name} (cont. {i+1})" if i > 0 else name
                embed.add_field(name=field_name, value=chunk, inline=inline)

    # ======================-
    # DRAFT LOTTERY COMMANDS
    # ======================-

    @discord.slash_command(name="draft", description="Run the dramatic draft lottery presentation")
    async def run_draft_lottery(self, ctx):
        
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
        
        await ctx.respond(embed=embed)
        await asyncio.sleep(3)
        
        for i in range(3, 0, -1):
            embed = discord.Embed(
                title="🎲 LOTTERY BEGINNING IN...",
                description=f"# {i}",
                color=0xe74c3c
            )
            await ctx.edit(embed=embed)
            await asyncio.sleep(1)
        
        embed = discord.Embed(
            title="🎱 DRAWING LOTTERY BALLS...",
            description="*The rocket league gods are deciding...*",
            color=0xf39c12
        )
        await ctx.edit(embed=embed)
        await asyncio.sleep(2)
        
        result = self.lottery.conduct_draft()
        self.last_result = result
        
        def get_pick_probability(player_name: str, pick_position: int, is_eliminated: bool = False) -> float:
            player_tier = None
            for tier, names in self.lottery.players.items():
                if player_name in names:
                    player_tier = tier
                    break
            
            if player_tier is None:
                return 0.0
            
            if is_eliminated:
                return 20.0
            else:
                base_weights = self.lottery.weights[player_tier]
                if pick_position <= len(base_weights):
                    return base_weights[pick_position - 1]
                else:
                    return 1.0
        
        eliminated_list = ""
        draft_list = ""
        
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
        
        sorted_draft = sorted(result.draft_order, key=lambda x: x[0], reverse=True)
        
        for i, (pick, player, tier) in enumerate(sorted_draft):
            pick_emoji = self.get_pick_emoji(pick)
            pick_chance = get_pick_probability(player, pick)
            
            draft_entry = f"{pick_emoji} **Pick #{pick}:** `{player}` ({pick_chance:.1f}%)\n"
            
            all_picks = []
            if draft_list:
                for line in draft_list.split('\n'):
                    if line.strip():
                        all_picks.append(line)
            all_picks.append(draft_entry.strip())
            
            def extract_pick_num(line):
                try:
                    return int(line.split('#')[1].split(':')[0])
                except:
                    return 999
            
            all_picks.sort(key=extract_pick_num)
            draft_list = '\n'.join(all_picks)
            
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
        
        tier_counts = {1: 0, 2: 0, 3: 0}
        for _, _, tier in result.draft_order:
            tier_counts[tier] += 1
        
        breakdown = f"Tier 1: {tier_counts[1]}/2\nTier 2: {tier_counts[2]}/5\nTier 3: {tier_counts[3]}/3"
        final_embed.add_field(name="📊 Draft Breakdown", value=breakdown, inline=True)
        
        final_embed.set_footer(text="The lottery has spoken! 🎱")
        
        await ctx.edit(embed=final_embed)

    @discord.slash_command(name="sim", description="Run simulation analysis")
    async def run_simulation(self, ctx, runs: int = 1000):
        if runs < 1 or runs > 10000:
            await ctx.respond("❌ Please choose between 1 and 10,000 simulations.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔄 Running Simulation...",
            description=f"Simulating {runs:,} draft lotteries...",
            color=0xf39c12
        )
        await ctx.respond(embed=embed)
        
        results = self.lottery.run_simulation(runs)
        
        embed = discord.Embed(
            title=f"📊 SIMULATION RESULTS ({runs:,} runs)",
            color=0x3498db
        )
        
        tier1_elim_pct = (results['tier1_eliminations'] / runs) * 100
        embed.add_field(
            name="🛡️ Tier 1 Protection",
            value=f"Eliminations: {results['tier1_eliminations']:,} / {runs:,} ({tier1_elim_pct:.3f}%)",
            inline=False
        )
        
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
        if not self.last_result:
            await ctx.respond("❌ No draft has been run yet. Use `/draft` to run a lottery!", ephemeral=True)
            return
        
        result = self.last_result
        
        draft_text = ""
        for pick, player, tier in result.draft_order:
            pick_emoji = self.get_pick_emoji(pick)
            draft_text += f"{pick_emoji} **Pick #{pick}:** `{player}`\n"
        
        embed = discord.Embed(
            title="🏆 LAST DRAFT RESULT",
            description=draft_text,
            color=0x1f8b4c
        )
        
        if result.eliminated:
            elim_text = ""
            for player, tier in result.eliminated:
                elim_text += f"💀 `{player}`\n"
            
            embed.add_field(
                name="❌ ELIMINATED PLAYERS",
                value=elim_text,
                inline=False
            )
        
        tier_counts = {1: 0, 2: 0, 3: 0}
        for _, _, tier in result.draft_order:
            tier_counts[tier] += 1
        
        breakdown = f"Tier 1: {tier_counts[1]}/2\nTier 2: {tier_counts[2]}/5\nTier 3: {tier_counts[3]}/3"
        embed.add_field(name="📊 Draft Breakdown", value=breakdown, inline=True)
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="tournament_seeding", description="Generate dramatic tournament seeding for 8 teams")
    @commands.has_permissions(administrator=True)
    async def tournament_seeding(self, ctx):
        try:
            teams = [
                "YNs", "Team 2", "Mulignans", "16 Keycaps",
                "Team 5", "Mounties", "Team 7", "Ice Truck Killers"
            ]
            
            shuffled_teams = teams.copy()
            random.shuffle(shuffled_teams)
            
            seeding = {}
            for i, team in enumerate(shuffled_teams, 1):
                seeding[i] = team
            
            embed = discord.Embed(
                title="🏆 TOURNAMENT SEEDING CEREMONY 🏆",
                description="The moment you've all been waiting for...\nThe seeds have been determined!\n\nDrumroll please... 🥁🥁🥁",
                color=0xffd700
            )
            await ctx.respond(embed=embed)
            await asyncio.sleep(3)
            
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

    # ======================-
    # SCHEDULING COMMANDS
    # ======================-

    @discord.slash_command(name="schedule_game", description="Start a game scheduling session between two teams")
    @commands.has_permissions(administrator=True)
    async def schedule_game(self, ctx, team1: str, team2: str):
        channel_id = ctx.channel.id
        
        if channel_id in self.active_sessions:
            await ctx.respond("There's already an active scheduling session in this channel. Use `/cancel_schedule` to cancel it first.", ephemeral=True)
            return
        
        new_session_obj = DBSchedulingSession(channel_id=str(channel_id), team1=team1, team2=team2)
        
        save_session(new_session_obj)
        session = load_session(channel_id)

        if not session:
            await ctx.respond("❌ **Error:** Could not save the new scheduling session to the database. Please check the logs.", ephemeral=True)
            return

        self.active_sessions[channel_id] = session
        
        embed = discord.Embed(
            title="🎮 Game Scheduling Started!",
            description=(
                f"**Scheduling game between {team1} and {team2}**\n\n"
                f"📋 **What Players Need to Do:**\n"
                f"All **6 players** (3 from each team) must use the `/my_schedule` command to set their availability.\n\n"
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

    @discord.slash_command(name="my_schedule", description="Set your weekly availability using a visual calendar interface")
    async def my_schedule(self, ctx):
        user_id = ctx.author.id
        
        session = load_session(ctx.channel.id)
        if not session:
            await ctx.respond("No active scheduling session found in this channel. Please ask an admin to start one with `/schedule_game`.", ephemeral=True)
            return
        self.active_sessions[ctx.channel.id] = session
        if not session:
            await ctx.respond("Could not load session data from the database.", ephemeral=True)
            return
        
        view = CalendarScheduleView(user_id, session, self, ctx.channel.id)
        
        embed = discord.Embed(
            title="📅 Set Your Weekly Availability",
            description="Use the buttons below to set your availability for each day.",
            color=0x0099ff
        )
        
        try:
            await ctx.author.send(embed=embed, view=view)
            await ctx.respond(f"{ctx.author.mention}, check your DMs for the scheduling interface!", ephemeral=True)
        except discord.Forbidden:
            await ctx.respond("I couldn't send you a DM. Please enable DMs from server members and try again.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Error sending calendar interface: {str(e)}", ephemeral=True)

    async def finalize_scheduling(self, channel, session):
        if not isinstance(session, DBSchedulingSession):
            print(f"Error: session is not DBSchedulingSession, it is {type(session)}")
            return

        # Try to find a time for all players first
        common_times_all = session.find_common_times(min_players=session.expected_players)
        
        if common_times_all:
            # Logic for 6/6 players (existing logic)
            best_day = None
            best_time = None
            best_date_info = None
            
            for date_info in session.schedule_dates:
                day_name = date_info['day_name']
                if day_name in common_times_all and common_times_all[day_name]:
                    best_day = day_name
                    best_date_info = date_info
                    # In 6/6 case, the structure is simpler: list of times
                    for time in common_times_all[day_name]:
                        hour = int(time.split(':')[0])
                        if 18 <= hour <= 22:
                            best_time = time
                            break
                    if not best_time:
                        best_time = common_times_all[day_name][0]
                    break
            
            if best_day and best_time and best_date_info:
                # Propose this time to the channel
                # (This is the existing logic for proposing a time)
                hour = int(best_time.split(':')[0])
                minute = best_time.split(':')[1]
                
                if hour == 0:
                    display_time = f"11:59 PM"
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
                
                session.proposed_times.append({
                    'day': best_day,
                    'time': best_time
                })
                save_session(session)
                
                embed = discord.Embed(
                    title="��� Proposed Game Time (6/6 Match!)",
                    description=f"**{best_date_info['full_date']} at {display_time}**",
                    color=0x00ff00
                )
                embed.add_field(
                    name="⚠️ Confirmation Required",
                    value="All players must confirm this time works for them using the buttons below.",
                    inline=False
                )
                
                team1_role = discord.utils.get(channel.guild.roles, name=session.team1)
                team2_role = discord.utils.get(channel.guild.roles, name=session.team2)
                team1_mention = f"<@&{team1_role.id}>" if team1_role else session.team1
                team2_mention = f"<@&{team2_role.id}>" if team2_role else session.team2

                view = ConfirmationView(session, game_info, self)
                message = await channel.send(f"{team1_mention} {team2_mention} Game Time: {best_date_info['full_date']} @ {display_time}", embed=embed, view=view)
                view.message = message
                return # Stop after proposing a 6/6 time

        # If no 6/6 time, try for 5/6
        common_times_5_of_6 = session.find_common_times(min_players=session.expected_players - 1)

        if common_times_5_of_6:
            best_day_5_of_6 = None
            best_time_info_5_of_6 = None
            best_date_info_5_of_6 = None

            for date_info in session.schedule_dates:
                day_name = date_info['day_name']
                if day_name in common_times_5_of_6 and common_times_5_of_6[day_name]:
                    best_day_5_of_6 = day_name
                    best_date_info_5_of_6 = date_info
                    best_time_info_5_of_6 = common_times_5_of_6[day_name][0] # Get the first available 5/6 slot
                    break
            
            if best_day_5_of_6 and best_time_info_5_of_6 and best_date_info_5_of_6:
                excluded_player_id = best_time_info_5_of_6['excluded_players'][0]
                user_to_dm = self.bot.get_user(int(excluded_player_id))

                if user_to_dm:
                    best_time = best_time_info_5_of_6['time']
                    hour = int(best_time.split(':')[0])
                    minute = best_time.split(':')[1]

                    if hour == 0:
                        display_time = f"11:59 PM"
                    elif hour < 12:
                        display_time = f"{hour}:{minute} AM"
                    elif hour == 12:
                        display_time = f"12:{minute} PM"
                    else:
                        display_time = f"{hour-12}:{minute} PM"
                    
                    game_info = {
                        'day': best_day_5_of_6, 
                        'time': display_time,
                        'full_date': best_date_info_5_of_6['full_date'],
                        'date': best_date_info_5_of_6['date']
                    }

                    session.proposed_times.append({
                        'day': best_day_5_of_6,
                        'time': best_time
                    })
                    save_session(session)

                    embed = discord.Embed(
                        title="Flexible Game Time Proposal",
                        description=f"We found a time that works for 5/6 players: **{game_info['full_date']} at {game_info['time']}**. Would you be able to make this time?",
                        color=0xffa500
                    )
                    
                    view = AskPlayerView(session, game_info, self)
                    await user_to_dm.send(embed=embed, view=view)
                    await channel.send(f"We couldn't find a time for all 6 players. A DM has been sent to {user_to_dm.mention} to ask if they can make a time that works for the other 5 players.")
                return

        # If no 6/6 or 5/6 times are found
        embed = discord.Embed(
            title="❌ No Common Times Found",
            description="Unfortunately, no times work for even 5 out of 6 players. Players should use `/my_schedule` to adjust their availability.",
            color=0xff0000
        )
        await channel.send(embed=embed)

    @discord.slash_command(name="next_game_time", description="Propose the next available game time.")
    @commands.has_permissions(administrator=True)
    async def next_game_time(self, ctx):
        channel_id = ctx.channel.id
        session = self.active_sessions.get(channel_id)
        if not session:
            session = load_session(channel_id)
            if not session:
                await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
                return
            self.active_sessions[channel_id] = session

        if len(session.player_schedules) < session.expected_players:
            await ctx.respond(f"Still waiting for {session.expected_players - len(session.player_schedules)} players to submit their availability.", ephemeral=True)
            return

        await self.finalize_scheduling(ctx.channel, session)
        await ctx.respond("Attempting to find and propose the next available game time.", ephemeral=True)

    def format_available_times_interactive(self, common_times, session):
        formatted = []
        for date_info in session.schedule_dates:
            day_name = date_info['day_name']
            if day_name in common_times and common_times[day_name]:
                times = common_times[day_name]
                display_times = []
                for time in times[:5]:
                    hour = int(time.split(':')[0])
                    minute = time.split(':')[1]
                    if hour == 0:
                        display_times.append(f"11:59 PM")
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
    @commands.has_permissions(administrator=True)
    async def cancel_schedule(self, ctx):
        channel_id = ctx.channel.id
        
        if channel_id in self.active_sessions:
            del self.active_sessions[channel_id]
            delete_session(channel_id)
            await ctx.respond("❌ Scheduling session cancelled.")
        else:
            await ctx.respond("No active scheduling session to cancel.", ephemeral=True)

    @discord.slash_command(name="schedule_status", description="Check the status of the current scheduling session")
    async def schedule_status(self, ctx):
        channel_id = ctx.channel.id
        
        session = self.active_sessions.get(channel_id)
        if not session:
            session = load_session(channel_id)
            if not session:
                await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
                return
            self.active_sessions[channel_id] = session

        submitted_players_count = len(session.player_schedules)
        remaining = session.expected_players - submitted_players_count
        
        embed = discord.Embed(
            title="📊 Scheduling Status",
            color=0x0099ff
        )
        embed.add_field(
            name="Progress",
            value=f"{submitted_players_count}/{session.expected_players} players completed their schedules",
            inline=False
        )
        
        if remaining > 0:
            embed.add_field(
                name="Remaining",
                value=f"Waiting for {remaining} more players to use `/my_schedule`",
                inline=False
            )
            
            submitted_players_list = []
            for user_id in session.player_schedules.keys():
                user = self.bot.get_user(int(user_id))
                player_name = user.display_name if user else f"User ID: {user_id}"
                submitted_players_list.append(player_name)
            
            if submitted_players_list:
                embed.add_field(
                    name="✅ Players Who Submitted Schedules",
                    value="\n".join(submitted_players_list),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Players Who Submitted Schedules",
                    value="None yet.",
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
            value=f"{session.team1} vs {session.team2}",
            inline=False
        )

        if remaining == 0: # Only show confirmed/unconfirmed if all schedules are in
            confirmed_players = []
            unconfirmed_players = []
            for user_id in session.player_schedules.keys():
                user = self.bot.get_user(int(user_id))
                player_name = user.display_name if user else f"User ID: {user_id}"
                if session.confirmations.get(user_id, False): # Default to False if not in confirmations
                    confirmed_players.append(player_name)
                else:
                    unconfirmed_players.append(player_name)

            if confirmed_players:
                embed.add_field(
                    name="✅ Confirmed Players",
                    value="\n".join(confirmed_players),
                    inline=False
                )
            else:
                embed.add_field(
                    name="✅ Confirmed Players",
                    value="None yet.",
                    inline=False
                )

            if unconfirmed_players:
                embed.add_field(
                    name="❌ Unconfirmed Players",
                    value="\n".join(unconfirmed_players),
                    inline=False
                )
            else:
                embed.add_field(
                    name="❌ Unconfirmed Players",
                    value="All players confirmed!",
                    inline=False
                )

        # Check for proposed game time
        proposed_game_time = None
        if session.proposed_times:
            # Get the last proposed time
            last_proposed = session.proposed_times[-1]
            # Convert 24-hour to 12-hour format for display
            hour = int(last_proposed['time'].split(':')[0])
            minute = last_proposed['time'].split(':')[1]
            if hour == 0:
                display_time = f"12:{minute} AM"
            elif hour < 12:
                display_time = f"{hour}:{minute} AM"
            elif hour == 12:
                display_time = f"12:{minute} PM"
            else:
                display_time = f"{hour-12}:{minute} PM"
            
            # Get full date info for the proposed day
            proposed_date_info = next((d for d in session.schedule_dates if d['day_name'] == last_proposed['day']), None)
            if proposed_date_info:
                proposed_game_time = f"**{proposed_date_info['full_date']} at {display_time}**"

        if proposed_game_time:
            confirmed_count = sum(1 for c in session.confirmations.values() if c)
            total_players_in_session = len(session.player_schedules) # Use player_schedules for total players
            
            if confirmed_count >= total_players_in_session and total_players_in_session > 0:
                embed.add_field(
                    name="✅ Confirmed Game Time",
                    value=proposed_game_time,
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎮 Proposed Game Time",
                    value=f"{proposed_game_time} ({confirmed_count}/{total_players_in_session} confirmed)",
                    inline=False
                )
            
            # Filter out the proposed time from common_times if it exists
            common_times = session.find_common_times()
            if common_times:
                proposed_day = last_proposed['day']
                proposed_time_24hr = last_proposed['time']
                if proposed_day in common_times and proposed_time_24hr in common_times[proposed_day]:
                    common_times[proposed_day] = [t for t in common_times[proposed_day] if t != proposed_time_24hr]
                    if not common_times[proposed_day]: # If no more times for that day, remove the day
                        del common_times[proposed_day]

            if common_times:
                common_text = ""
                time_slots_display = {
                    '18:00': '6 PM', '19:00': '7 PM', '20:00': '8 PM',
                    '21:00': '9 PM', '22:00': '10 PM', '23:00': '11 PM', '00:00': '11:59 PM'
                }
                for day_name, times in common_times.items():
                    date_info = session.get_date_info(day_name)
                    day_display = f"{date_info['day_name']}, {date_info['date']}" if date_info else day_name

                    # Custom sorting for display: move '00:00' to the end
                    sorted_times = sorted([t for t in times if t != '00:00'])
                    if '00:00' in times:
                        sorted_times.append('00:00')

                    time_display = [time_slots_display.get(t, t) for t in sorted_times]

                    common_text += f"**{day_display}:** {', '.join(time_display)}\n"

                embed.add_field(
                    name="🎯 Other Possible Game Times",
                    value=common_text,
                    inline=False
                )
            elif not proposed_game_time: # Only show "No Common Times" if no game is proposed
                embed.add_field(
                    name="⚠️ No Common Times",
                    value="No times work for all players yet.",
                    inline=False
                )
        else: # No proposed game time, show all common times
            common_times = session.find_common_times()
            if common_times:
                common_text = ""
                time_slots_display = {
                    '18:00': '6 PM', '19:00': '7 PM', '20:00': '8 PM',
                    '21:00': '9 PM', '22:00': '10 PM', '23:00': '11 PM', '00:00': '11:59 PM'
                }
                for day_name, times in common_times.items():
                    date_info = session.get_date_info(day_name)
                    day_display = f"{date_info['day_name']}, {date_info['date']}" if date_info else day_name

                    # Custom sorting for display: move '00:00' to the end
                    sorted_times = sorted([t for t in times if t != '00:00'])
                    if '00:00' in times:
                        sorted_times.append('00:00')

                    time_display = [time_slots_display.get(t, t) for t in sorted_times]

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
        
        await ctx.respond(embed=embed)
    
    @discord.slash_command(name="view_all_availability", description="View all submitted schedules for the current session")
    @commands.has_permissions(administrator=True)
    async def view_all_availability(self, ctx):
        await ctx.defer()

        try:
            from models.scheduling import get_all_active_sessions
            
            active_sessions = get_all_active_sessions()
            
            if not active_sessions:
                await ctx.followup.send("No active scheduling sessions found.")
                return

            # For simplicity, let's assume we're interested in the session for the current channel first
            # Or, if multiple, we can list them out. For now, let's focus on the current channel's session.
            current_channel_session = next((s for s in active_sessions if str(s.channel_id) == str(ctx.channel.id)), None)

            if not current_channel_session:
                # If no session for current channel, list all active sessions
                embed = discord.Embed(
                    title="Active Scheduling Sessions",
                    description="No active session in this channel. Here are sessions in other channels:",
                    color=0x0099ff
                )
                for session in active_sessions:
                    embed.add_field(
                        name=f"Channel ID: {session.channel_id}",
                        value=f"Teams: {session.team1} vs {session.team2}\nPlayers: {len(session.player_schedules)}/{session.expected_players}",
                        inline=False
                    )
                await ctx.followup.send(embed=embed)
                return

            session = current_channel_session
            
            if not session.player_schedules:
                await ctx.followup.send(f"No schedules submitted yet for {session.team1} vs {session.team2} in this channel.")
                return

            embed = discord.Embed(
                title=f"Schedules for {session.team1} vs {session.team2}",
                description=f"**Channel:** <#{session.channel_id}>\n**Players Submitted:** {len(session.player_schedules)}/{session.expected_players}",
                color=0x0099ff
            )

            for user_id, player_schedule in session.player_schedules.items():
                user = self.bot.get_user(int(user_id))
                player_name = user.display_name if user else f"User ID: {user_id}"
                
                schedule_text = []
                for day_name, times in player_schedule.items():
                    if times:
                        # Convert 24-hour to 12-hour format for display
                        display_times = []
                        for time_str in times:
                            hour = int(time_str.split(':')[0])
                            minute = time_str.split(':')[1]
                            if hour == 0:
                                display_times.append(f"12:{minute} AM")
                            elif hour < 12:
                                display_times.append(f"{hour}:{minute} AM")
                            elif hour == 12:
                                display_times.append(f"12:{minute} PM")
                            else:
                                display_times.append(f"{hour-12}:{minute} PM")
                        schedule_text.append(f"**{day_name}:** {', '.join(display_times)}")
                    else:
                        schedule_text.append(f"**{day_name}:** Not Available")
                
                embed.add_field(
                    name=f"👤 {player_name}",
                    value="\n".join(schedule_text) if schedule_text else "No schedule details.",
                    inline=False
                )
            
            await ctx.followup.send(embed=embed)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await ctx.followup.send(f"An error occurred while fetching schedules: {str(e)}", ephemeral=True)

    @discord.slash_command(name="current_game_proposal", description="Show the currently proposed game time and confirmation status.")
    async def current_game_proposal(self, ctx):
        channel_id = ctx.channel.id
        session = self.active_sessions.get(channel_id)
        if not session:
            session = load_session(channel_id)
            if not session:
                await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
                return
            self.active_sessions[channel_id] = session

        if not session.proposed_times:
            await ctx.respond("No game time has been proposed yet for this session.", ephemeral=True)
            return

        last_proposed = session.proposed_times[-1]
        
        # Convert 24-hour to 12-hour format for display
        hour = int(last_proposed['time'].split(':')[0])
        minute = last_proposed['time'].split(':')[1]
        if hour == 0:
            display_time = f"11:59 PM"
        elif hour < 12:
            display_time = f"{hour}:{minute} AM"
        elif hour == 12:
            display_time = f"12:{minute} PM"
        else:
            display_time = f"{hour-12}:{minute} PM"
        
        # Get full date info for the proposed day
        proposed_date_info = next((d for d in session.schedule_dates if d['day_name'] == last_proposed['day']), None)
        
        if not proposed_date_info:
            await ctx.respond("Error: Could not retrieve full date information for the proposed time.", ephemeral=True)
            return

        game_info = {
            'day': last_proposed['day'], 
            'time': display_time,
            'full_date': proposed_date_info['full_date'],
            'date': proposed_date_info['date']
        }

        embed = discord.Embed(
            title="🎮 Proposed Game Time",
            description=f"**{proposed_date_info['full_date']} at {display_time}**",
            color=0xffa500
        )
        embed.add_field(
            name="⚠️ Confirmation Required",
            value="All players must confirm this time works for them using the buttons below.",
            inline=False
        )
        
        # Add confirmation status to the embed
        confirmed_count = sum(1 for c in session.confirmations.values() if c)
        total_players_in_session = len(session.player_schedules)
        embed.add_field(
            name="Current Confirmation Status",
            value=f"{confirmed_count}/{total_players_in_session} confirmed",
            inline=False
        )

        confirmed_players = []
        unconfirmed_players = []
        for user_id in session.player_schedules.keys():
            user = self.bot.get_user(int(user_id))
            player_name = user.display_name if user else f"User ID: {user_id}"
            if session.confirmations.get(user_id, False):
                confirmed_players.append(player_name)
            else:
                unconfirmed_players.append(player_name)

        if confirmed_players:
            embed.add_field(
                name="✅ Confirmed Players",
                value="\n".join(confirmed_players),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Confirmed Players",
                value="None yet.",
                inline=False
            )

        if unconfirmed_players:
            embed.add_field(
                name="❌ Unconfirmed Players",
                value="\n".join(unconfirmed_players),
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Unconfirmed Players",
                value="All players confirmed!",
                inline=False
            )

        team1_role = discord.utils.get(ctx.guild.roles, name=session.team1)
        team2_role = discord.utils.get(ctx.guild.roles, name=session.team2)
        team1_mention = f"<@&{team1_role.id}>" if team1_role else session.team1
        team2_mention = f"<@&{team2_role.id}>" if team2_role else session.team2

        view = ConfirmationView(session, game_info, self)
        message = await ctx.respond(f"{team1_mention} {team2_mention} Game Time: {proposed_date_info['full_date']} @ {display_time}", embed=embed, view=view)
        view.message = message

    @discord.slash_command(name="db_health", description="Check database health and connection")
    @commands.has_permissions(administrator=True)
    async def db_health(self, ctx):
        try:
            from models.scheduling import engine, get_all_active_sessions
            from sqlalchemy import text
            import time
            
            start_time = time.time()
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            connection_time = (time.time() - start_time) * 1000
            
            db_url = str(engine.url)
            db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
            
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
        await ctx.defer(ephemeral=True)
        try:
            import io
            
            sessions_data = {}
            
            for channel_id, session in self.active_sessions.items():
                sessions_data[str(channel_id)] = {
                    'teams': [session.team1, session.team2],
                    'player_schedules': session.player_schedules,
                    'players_responded': list(session.players_responded),
                    'schedule_dates': session.schedule_dates,
                    'expected_players': session.expected_players,
                    'confirmations': getattr(session, 'confirmations', {})
                }
            
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
        try:
            from models.scheduling import get_all_active_sessions
            
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
            
            db_session_info = []
            if db_sessions:
                for s in db_sessions:
                    db_session_info.append(f"Channel {s.channel_id}: {s.team1} vs {s.team2} (Active: {s.is_active})")

            embed.add_field(
                name="Database Sessions", 
                value=f"{len(db_sessions)} sessions\n" + "\n".join(db_session_info) if db_sessions else "None",
                inline=False
            )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"Error: {str(e)}", ephemeral=True)

    @discord.slash_command(name="reload_sessions", description="Manually reload sessions from database")
    @commands.has_permissions(administrator=True)
    async def reload_sessions(self, ctx):
        embed = discord.Embed(
            title="🔄 Sessions Reloaded",
            description="",
            color=0x00ff00
        )
        try:
            from models.scheduling import get_all_active_sessions
            
            old_count = len(self.active_sessions)
            self.active_sessions.clear()
            
            db_sessions = get_all_active_sessions()
            loaded_count = 0
            
            for db_session in db_sessions:
                try:
                    self.active_sessions[int(db_session.channel_id)] = db_session
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

    @discord.slash_command(name="cleanup_duplicate_players", description="Admin command to clean up duplicate players in active sessions.")
    @commands.has_permissions(administrator=True)
    async def cleanup_duplicate_players(self, ctx):
        await ctx.defer(ephemeral=True)
        
        active_sessions = get_all_active_sessions()
        cleaned_sessions = 0
        
        for session in active_sessions:
            # No longer need to clean up players_responded as it's derived from player_schedules
            # This command can now be used to ensure data integrity if player_schedules somehow gets duplicates
            # For now, it will just report on sessions.
            pass # No action needed here as player_schedules should inherently handle uniqueness
                
        await ctx.followup.send(f"✅ Database cleanup complete. Scanned {len(active_sessions)} active sessions. No duplicate player entries to clean up based on current logic.", ephemeral=True)

    @discord.slash_command(name="export_schedules", description="Export all schedules for the current session to a JSON file")
    @commands.has_permissions(administrator=True)
    async def export_schedules(self, ctx):
        try:
            import io
            channel_id = ctx.channel.id
            
            if channel_id not in self.active_sessions:
                await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
                return
            
            session = self.active_sessions[channel_id]
            
            if not session.player_schedules:
                await ctx.respond("No schedules have been submitted yet.", ephemeral=True)
                return
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "teams": [session.team1, session.team2],
                "channel_id": str(channel_id),
                "schedule_dates": session.schedule_dates,
                "player_count": len(session.player_schedules),
                "expected_players": session.expected_players,
                "players": {}
            }
            
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
            
            json_data = json.dumps(export_data, indent=2, default=str)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"schedules_{session.team1.replace(' ', '_')}_vs_{session.team2.replace(' ', '_')}_{timestamp}.json"
            
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

    @discord.slash_command(name="remove_player_schedule", description="Remove a player's schedule from the current session.")
    @commands.has_permissions(administrator=True)
    async def remove_player_schedule(self, ctx, user_id: str):
        channel_id = ctx.channel.id
        session = self.active_sessions.get(channel_id)
        if not session:
            session = load_session(channel_id)
            if not session:
                await ctx.respond("No active scheduling session in this channel.", ephemeral=True)
                return
            self.active_sessions[channel_id] = session

        if user_id in session.player_schedules:
            del session.player_schedules[user_id]
            save_session(session)
            await ctx.respond(f"✅ Schedule for user ID {user_id} removed from this session.", ephemeral=True)
        else:
            await ctx.respond(f"User ID {user_id} does not have a submitted schedule in this session.", ephemeral=True)

class CalendarScheduleView(discord.ui.View):
    def __init__(self, user_id, session, cog, channel_id):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.session = session
        self.cog = cog
        self.channel_id = channel_id
        self.schedule_state = {}
        self.current_day_index = 0

        existing_schedule = self.session.player_schedules.get(str(self.user_id), {})
        for date_info in self.session.schedule_dates:
            day_name = date_info['day_name']
            self.schedule_state[day_name] = {}
            
            if day_name in existing_schedule:
                existing_times = existing_schedule[day_name]
                if not existing_times:
                    self.schedule_state[day_name]['status'] = 'not_available'
                elif len(existing_times) >= 6:
                    self.schedule_state[day_name]['status'] = 'all_day'
                else:
                    self.schedule_state[day_name]['status'] = 'partial'
                    for time_slot in ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']:
                        self.schedule_state[day_name][time_slot] = time_slot in existing_times
            else:
                self.schedule_state[day_name]['status'] = None
        
        self.create_calendar_buttons()

    def create_calendar_buttons(self):
        self.clear_items()
        current_date_info = self.session.schedule_dates[self.current_day_index]
        current_day_name = current_date_info['day_name']

        prev_button = discord.ui.Button(label="◀ Prev Day", style=discord.ButtonStyle.secondary, row=0)
        prev_button.callback = self.prev_day_callback
        self.add_item(prev_button)

        day_display_button = discord.ui.Button(
            label=f"{current_date_info['day_name']}, {current_date_info['date']}",
            style=discord.ButtonStyle.primary,
            disabled=True,
            row=0
        )
        self.add_item(day_display_button)

        next_button = discord.ui.Button(label="Next Day ▶", style=discord.ButtonStyle.secondary, row=0)
        next_button.callback = self.next_day_callback
        self.add_item(next_button)

        time_slots = ['6PM', '7PM', '8PM', '9PM', '10PM', '11PM', '12AM']
        time_values = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']

        for i, (time_label, time_value) in enumerate(zip(time_slots, time_values)):
            is_selected = self.schedule_state[current_day_name].get(time_value, False)
            day_status = self.schedule_state[current_day_name].get('status')

            style = discord.ButtonStyle.gray
            if day_status == 'all_day':
                style = discord.ButtonStyle.green
            elif day_status == 'not_available':
                style = discord.ButtonStyle.red
            elif is_selected:
                style = discord.ButtonStyle.green

            row = 1 if i < 4 else 2
            time_button = TimeSlotButton(label=time_label, time_value=time_value, day_name=current_day_name, style=style, row=row)
            self.add_item(time_button)

        all_day_button = DayActionButton(label="All Day Available", action="all_day", style=discord.ButtonStyle.blurple, row=3)
        self.add_item(all_day_button)

        not_available_button = DayActionButton(label="Not Available", action="not_available", style=discord.ButtonStyle.red, row=3)
        self.add_item(not_available_button)

        finalize_button = discord.ui.Button(label="✅ Finalize Schedule", style=discord.ButtonStyle.green, row=4)
        finalize_button.callback = self.finalize_schedule_callback
        self.add_item(finalize_button)

    async def prev_day_callback(self, interaction: discord.Interaction):
        self.current_day_index = (self.current_day_index - 1) % 7
        self.create_calendar_buttons()
        await interaction.response.edit_message(view=self)

    async def next_day_callback(self, interaction: discord.Interaction):
        self.current_day_index = (self.current_day_index + 1) % 7
        self.create_calendar_buttons()
        await interaction.response.edit_message(view=self)

    async def finalize_schedule_callback(self, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("This is not your schedule!", ephemeral=True)
                return

            session = load_session(self.channel_id)
            if not session:
                await interaction.response.send_message("Error: Could not find the scheduling session.", ephemeral=True)
                return

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

            if len(player_schedule_for_db) < 7:
                await interaction.response.send_message(f"Please set all 7 days before finalizing! You have {len(player_schedule_for_db)}/7 days set.", ephemeral=True)
                return

            session.player_schedules[str(self.user_id)] = player_schedule_for_db

            save_session(session)
            # Reload the session from the database to ensure the cache is updated with the latest data
            updated_session = load_session(session.channel_id)
            if updated_session:
                self.cog.active_sessions[int(updated_session.channel_id)] = updated_session
                session = updated_session # Use the reloaded session for subsequent operations

            channel = self.cog.bot.get_channel(int(session.channel_id))
            remaining = session.expected_players - len(session.player_schedules)

            if remaining > 0:
                await channel.send(f"📝 {interaction.user.display_name} finalized their schedule. Waiting for {remaining} more players...")
            else:
                await channel.send(f"🎉 All players have submitted their schedules! Initiating game time proposal...")

            await interaction.response.edit_message(
                content="✅ **Schedule finalized!** Thank you for submitting your availability.",
                embed=None,
                view=None
            )

            if len(session.player_schedules) >= session.expected_players:
                await self.cog.finalize_scheduling(channel, session)

        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(f"An unexpected error occurred during finalization: {e}", ephemeral=True)

class TimeSlotButton(discord.ui.Button):
    def __init__(self, label, time_value, day_name, style, row):
        super().__init__(label=label, style=style, row=row)
        self.time_value = time_value
        self.day_name = day_name

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return

        current_state = view.schedule_state[self.day_name].get(self.time_value, False)
        view.schedule_state[self.day_name][self.time_value] = not current_state
        view.schedule_state[self.day_name]['status'] = 'partial'
        view.create_calendar_buttons()
        await interaction.response.edit_message(view=view)

class DayActionButton(discord.ui.Button):
    def __init__(self, label, action, style, row):
        super().__init__(label=label, style=style, row=row)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user.id != view.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return

        day_name = view.session.schedule_dates[view.current_day_index]['day_name']
        view.schedule_state[day_name]['status'] = self.action
        view.create_calendar_buttons()
        await interaction.response.edit_message(view=view)

def setup(bot):
    bot.add_cog(DraftLotteryCog(bot))