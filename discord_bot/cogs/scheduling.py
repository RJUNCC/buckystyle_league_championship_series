# cogs/scheduling.py
import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Import database functions - updated for PostgreSQL support
from models.scheduling import (
    save_session, load_session, delete_session, 
    get_all_active_sessions, SchedulingSession as DBSchedulingSession
)
from models.player import Player

class EnhancedSchedulingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}
        
        # Load active sessions from database on startup
        self.bot.loop.create_task(self.load_active_sessions())

    async def load_active_sessions(self):
        """Load all active sessions from database on startup"""
        print("DEBUG: Attempting to load active sessions from database...")
        try:
            await self.bot.wait_until_ready()
            print("DEBUG: Bot is ready, proceeding to load sessions.")

            active_sessions = get_all_active_sessions()
            print(f"DEBUG: Found {len(active_sessions)} active sessions in database.")

            for db_session in active_sessions:
                try:
                    session = SchedulingSession.from_db(db_session)
                    self.active_sessions[int(db_session.channel_id)] = session
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

    @discord.slash_command(name="schedule_game_v2", description="Start a game scheduling session between two teams")
    async def schedule_game(self, ctx, team1: str, team2: str):
        """Start a game scheduling session with persistent database storage"""
        channel_id = ctx.channel.id
        
        # Check if there's already an active session in this channel
        if channel_id in self.active_sessions:
            await ctx.respond("There's already an active scheduling session in this channel. Use `/cancel_schedule` to cancel it first.", ephemeral=True)
            return
        
        # Create new scheduling session
        session = SchedulingSession(channel_id, [team1, team2])
        self.active_sessions[channel_id] = session
        session.save()  # Persist to database immediately
        
        embed = discord.Embed(
            title="🎮 Game Scheduling Started!",
            description=(
                f"**Scheduling game between {team1} and {team2}**\n\n"
                f"📋 **What Players Need to Do:**\n"
                f"All **6 players** (3 from each team) must use: `/my_schedule` or `/my_schedule2`\n\n"
                f"🕐 **Available Commands:**\n"
                f"• `/my_schedule` - Interactive dropdown interface\n"
                f"• `/my_schedule2` - Visual calendar interface\n\n"
                f"🎯 **Process:**\n"
                f"1️⃣ All 6 players set their weekly availability\n"
                f"2️⃣ Bot finds common times and proposes game time\n"
                f"3️⃣ All players confirm with ✅/❌ buttons\n"
                f"4️⃣ If anyone declines, they update schedule and repeat\n\n"
                f"⏳ **Progress:** Waiting for {session.expected_players} players...\n"
                f"💾 **Persistent:** This session will survive bot restarts!"
            ),
            color=0x00ff00
        )
        embed.set_footer(text="Choose /my_schedule (dropdown) or /my_schedule2 (calendar) to start!")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="schedule_status_v2", description="Check the status of the current scheduling session")
    async def schedule_status(self, ctx):
        """Check the status with database persistence info"""
        channel_id = ctx.channel.id
        
        if channel_id not in self.active_sessions:
            # Try to load from database
            db_session = load_session(channel_id)
            if db_session:
                session = SchedulingSession.from_db(db_session)
                self.active_sessions[channel_id] = session
            else:
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
                value=f"Waiting for {remaining} more players to use `/my_schedule` or `/my_schedule2`",
                inline=False
            )
            
            # Show who has responded
            if session.players_responded:
                responded_users = []
                for user_id in session.players_responded:
                    try:
                        user = self.bot.get_user(int(user_id))
                        responded_users.append(user.display_name if user else f"User {user_id}")
                    except:
                        responded_users.append(f"User {user_id}")
                
                embed.add_field(
                    name="✅ Completed",
                    value=", ".join(responded_users),
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
        
        embed.add_field(
            name="💾 Database",
            value="✅ Session persisted to database",
            inline=True
        )
        
        # Show schedule dates
        if session.schedule_dates:
            date_range = f"{session.schedule_dates[0]['full_date']} to {session.schedule_dates[-1]['full_date']}"
            embed.add_field(
                name="📅 Schedule Window",
                value=date_range,
                inline=True
            )
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="cancel_schedule_v2", description="Cancel the current scheduling session")
    async def cancel_schedule(self, ctx):
        """Cancel the current scheduling session and clean up database"""
        channel_id = ctx.channel.id
        
        if channel_id in self.active_sessions:
            # Remove from memory and database
            del self.active_sessions[channel_id]
            delete_session(channel_id)
            await ctx.respond("❌ Scheduling session cancelled and removed from database.")
        else:
            # Check if it exists in database only
            db_session = load_session(channel_id)
            if db_session:
                delete_session(channel_id)
                await ctx.respond("❌ Scheduling session found in database and cancelled.")
            else:
                await ctx.respond("No active scheduling session to cancel.", ephemeral=True)

    @discord.slash_command(name="cleanup_old_sessions", description="Clean up old scheduling sessions")
    @commands.has_permissions(administrator=True)
    async def cleanup_old_sessions(self, ctx, days_old: int = 7):
        """Clean up sessions older than specified days"""
        try:
            from models.scheduling import cleanup_old_sessions
            cleaned_count = cleanup_old_sessions(days_old)
            
            embed = discord.Embed(
                title="🧹 Database Cleanup Complete",
                description=f"Cleaned up {cleaned_count} sessions older than {days_old} days.",
                color=0x00ff00
            )
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error during cleanup: {str(e)}", ephemeral=True)

    @discord.slash_command(name="backup_sessions", description="Backup current scheduling sessions")
    @commands.has_permissions(administrator=True)
    async def backup_sessions(self, ctx):
        """Export current sessions for backup"""
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
                await ctx.respond("No active sessions to backup.", ephemeral=True)
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
            
            await ctx.respond(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"Error creating backup: {str(e)}", ephemeral=True)

    @discord.slash_command(name="db_health", description="Check database health and connection")
    @commands.has_permissions(administrator=True)
    async def db_health(self, ctx):
        """Check database health and connection status"""
        try:
            from models.scheduling import engine
            import time
            
            # Test connection
            start_time = time.time()
            
            # Try a simple query
            with engine.connect() as conn:
                result = conn.execute("SELECT 1")
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

    @discord.slash_command(name="my_schedule", description="Set your weekly availability using a modern calendar interface")
    async def my_schedule_v2(self, ctx):
        """Modern calendar interface for setting weekly availability"""
        channel_id = ctx.channel.id
        
        # Check for active session
        if channel_id not in self.active_sessions:
            await ctx.respond("No active scheduling session in this channel. Use `/schedule_game_v2` to start one.", ephemeral=True)
            return
        
        session = self.active_sessions[channel_id]
        
        # Create and send the view
        view = ScheduleView(ctx.author.id, session, self)
        
        embed = discord.Embed(
            title="📅 Set Your Weekly Availability",
            description="Click the buttons to navigate days and set your available times.",
            color=0x0099ff
        )
        
        await ctx.respond(embed=embed, view=view, ephemeral=True)

# Simple SchedulingSession class for this cog
class SchedulingSession:
    def __init__(self, channel_id, teams):
        self.channel_id = channel_id
        self.teams = teams
        self.player_schedules = {}
        self.players_responded = set()
        self.expected_players = 6
        self.confirmations = {}
        
        # Generate the next 7 days starting from tomorrow
        self.schedule_dates = self.generate_next_week()
    
    def generate_next_week(self):
        """Generate the next 7 days starting from tomorrow with actual dates"""
        dates = []
        start_date = datetime.now() + timedelta(days=1)
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            dates.append({
                'day_name': current_date.strftime('%A'),
                'date': current_date.strftime('%m/%d'),
                'full_date': current_date.strftime('%A, %B %d'),
            })
        
        return dates
    
    def save(self):
        """Save current state to database"""
        save_session(self)
    
    @classmethod
    def from_db(cls, db_session):
        """Create a SchedulingSession from database data"""
        session = cls(int(db_session.channel_id), [db_session.team1, db_session.team2])
        session.player_schedules = db_session.player_schedules or {}
        session.players_responded = set(db_session.players_responded or [])
        session.expected_players = db_session.expected_players
        session.schedule_dates = db_session.schedule_dates or session.generate_next_week()
        session.confirmations = db_session.confirmations or {}
        return session
    
    def add_player_schedule(self, user_id, schedule):
        self.player_schedules[user_id] = schedule
        self.players_responded.add(user_id)
        self.save()
        
    def is_complete(self):
        return len(self.players_responded) >= self.expected_players

class ScheduleView(discord.ui.View):
    def __init__(self, user_id, session, cog):
        super().__init__(timeout=600)  # 10 minute timeout
        self.user_id = user_id
        self.session = session
        self.cog = cog  # Direct reference to the cog
        self.current_day_index = 0
        
        # Initialize schedule state
        self.schedule_state = {}
        existing_schedule = self.session.player_schedules.get(str(self.user_id), {})
        
        for date_info in self.session.schedule_dates:
            day_name = date_info['day_name']
            self.schedule_state[day_name] = {}
            
            if day_name in existing_schedule:
                day_data = existing_schedule[day_name]
                if not day_data:
                    self.schedule_state[day_name]['status'] = 'not_available'
                elif len(day_data) >= 6:
                    self.schedule_state[day_name]['status'] = 'all_day'
                else:
                    self.schedule_state[day_name]['status'] = 'partial'
                    for time_slot in ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']:
                        self.schedule_state[day_name][time_slot] = time_slot in day_data
            else:
                self.schedule_state[day_name]['status'] = None
                
        self.create_calendar_buttons()

    def create_calendar_buttons(self):
        """Create the calendar interface"""
        self.clear_items()
        
        current_date_info = self.session.schedule_dates[self.current_day_index]
        current_day_name = current_date_info['day_name']
        
        # Row 0: Day navigation
        self.add_item(DayNavButton("◀ Prev", -1))
        self.add_item(discord.ui.Button(label=f"{current_date_info['day_name']}, {current_date_info['date']}", style=discord.ButtonStyle.primary, disabled=True, row=0))
        self.add_item(DayNavButton("Next ▶", 1))
        
        # Row 1 & 2: Time slots
        time_slots = ['6PM', '7PM', '8PM', '9PM', '10PM', '11PM', '12AM']
        time_values = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']
        
        for i, (label, value) in enumerate(zip(time_slots, time_values)):
            is_selected = self.schedule_state[current_day_name].get(value, False)
            day_status = self.schedule_state[current_day_name].get('status')
            
            style = discord.ButtonStyle.gray
            if day_status == 'all_day' or is_selected:
                style = discord.ButtonStyle.green
            elif day_status == 'not_available':
                style = discord.ButtonStyle.red
            elif day_status == 'unsure':
                style = discord.ButtonStyle.secondary
            
            self.add_item(TimeSlotButton(label, value, current_day_name, style, row=1 if i < 4 else 2))
            
        # Row 3: Day actions
        self.add_item(DayActionButton("All Day", "all_day", current_day_name, discord.ButtonStyle.blurple, 3))
        self.add_item(DayActionButton("Not Available", "not_available", current_day_name, discord.ButtonStyle.red, 3))
        self.add_item(DayActionButton("Unsure", "unsure", current_day_name, discord.ButtonStyle.secondary, 3))
        
        # Row 4: Control buttons
        self.add_item(CancelButton())
        self.add_item(FinalizeButton())

    async def update_message(self, interaction):
        """Update the message with the current schedule state"""
        self.create_calendar_buttons()
        
        embed = discord.Embed(
            title="📅 Set Your Weekly Availability",
            description="Click time slots or use the action buttons to set your availability for each day.",
            color=0x0099ff
        )
        
        status_text = ""
        days_completed = 0
        for date_info in self.session.schedule_dates:
            day_name = date_info['day_name']
            day_status = self.schedule_state[day_name].get('status')
            
            if day_status == 'all_day':
                status_text += f"**{date_info['full_date']}:** ✅ All Day\n"
                days_completed += 1
            elif day_status == 'not_available':
                status_text += f"**{date_info['full_date']}:** ❌ Not Available\n"
                days_completed += 1
            elif day_status == 'unsure':
                status_text += f"**{date_info['full_date']}:** ❓ Unsure\n"
                days_completed += 1
            elif day_status == 'partial':
                selected_times = [f"{int(t.split(':')[0]) % 12 or 12}{'AM' if t.startswith('00') else 'PM'}" 
                                  for t in ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00'] 
                                  if self.schedule_state[day_name].get(t)]
                if selected_times:
                    status_text += f"**{date_info['full_date']}:** ✅ {', '.join(selected_times)}\n"
                    days_completed += 1
                else:
                    status_text += f"**{date_info['full_date']}:** ⏳ In Progress\n"
            else:
                status_text += f"**{date_info['full_date']}:** ⏳ Not Set\n"
        
        embed.add_field(name=f"Progress: {days_completed}/7 Days Set", value=status_text, inline=False)
        
        if days_completed == 7:
            embed.color = 0x00ff00
            embed.add_field(name="🎉 Ready to Finalize!", value="Click 'Finalize' to submit your schedule.", inline=False)
            
        await interaction.response.edit_message(embed=embed, view=self)

class DayNavButton(discord.ui.Button):
    def __init__(self, label, direction):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=0)
        self.direction = direction
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        self.view.current_day_index = (self.view.current_day_index + self.direction) % len(self.view.session.schedule_dates)
        await self.view.update_message(interaction)

class TimeSlotButton(discord.ui.Button):
    def __init__(self, label, time_value, day_name, style, row):
        super().__init__(label=label, style=style, row=row)
        self.time_value = time_value
        self.day_name = day_name
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        current_state = self.view.schedule_state[self.day_name].get(self.time_value, False)
        self.view.schedule_state[self.day_name][self.time_value] = not current_state
        self.view.schedule_state[self.day_name]['status'] = 'partial'
        
        await self.view.update_message(interaction)

class DayActionButton(discord.ui.Button):
    def __init__(self, label, action, day_name, style, row):
        super().__init__(label=label, style=style, row=row)
        self.action = action
        self.day_name = day_name
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        self.view.schedule_state[self.day_name]['status'] = self.action
        for time_slot in ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']:
            if time_slot in self.view.schedule_state[self.day_name]:
                del self.view.schedule_state[self.day_name][time_slot]
                
        await self.view.update_message(interaction)

class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.red, row=4)
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        await interaction.response.edit_message(content="❌ Schedule setup cancelled.", embed=None, view=None)

class FinalizeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Finalize", style=discord.ButtonStyle.green, row=4)
        
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("This is not your schedule!", ephemeral=True)
            return
            
        user_schedule = {}
        for date_info in self.view.session.schedule_dates:
            day_name = date_info['day_name']
            day_state = self.view.schedule_state[day_name]
            day_status = day_state.get('status')
            
            if day_status == 'all_day':
                user_schedule[day_name] = ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00']
            elif day_status in ['not_available', 'unsure']:
                user_schedule[day_name] = []
            elif day_status == 'partial':
                user_schedule[day_name] = [t for t in ['18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00'] if day_state.get(t)]
            else:
                user_schedule[day_name] = []
                
        days_set = sum(1 for day_data in self.view.schedule_state.values() if day_data.get('status') is not None)
        if days_set < 7:
            await interaction.response.send_message(f"Please set all 7 days before finalizing! You have {days_set}/7 days set.", ephemeral=True)
            return
            
        self.view.session.add_player_schedule(str(self.view.user_id), user_schedule)
        
        if self.view.cog:
            channel = self.view.cog.bot.get_channel(self.view.session.channel_id)
            remaining = self.view.session.expected_players - len(self.view.session.players_responded)
            
            if remaining > 0:
                await channel.send(f"📝 {interaction.user.display_name} finalized their schedule. Waiting for {remaining} more players...")
            
            await interaction.response.edit_message(content="✅ **Schedule finalized!** Thank you.", embed=None, view=None)
            
            if self.view.session.is_complete():
                await self.view.cog.finalize_scheduling(channel, self.view.session)
        else:
            await interaction.response.send_message("Error: Could not find the scheduling session. Please try again.", ephemeral=True)

def setup(bot):
    bot.add_cog(EnhancedSchedulingCog(bot))