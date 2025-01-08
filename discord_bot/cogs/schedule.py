import discord
from discord.ext import commands
import sqlite3
from scheduling.schedule_matches import schedule_match, retry_failed_scheduling, load_team_stats
from scheduling.database import DB_NAME

class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="add_availability")
    async def add_availability(self, ctx, date: str, time_start: str, time_end: str):
        """
        Command for players to add their availability.
        Usage: !add_availability YYYY-MM-DD HH:MM HH:MM
        """
        player_name = ctx.author.name

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            UPDATE availability
            SET date = ?, time_start = ?, time_end = ?
            WHERE player_name = ?
            """, (date, time_start, time_end, player_name))
            conn.commit()

            if cursor.rowcount > 0:
                await ctx.send(f"✅ Availability updated for {player_name} on {date} from {time_start} to {time_end}.")
            else:
                await ctx.send(f"⚠️ No record found for {player_name}. Please ensure you are listed in the system.")
        except Exception as e:
            await ctx.send(f"❌ Failed to update availability: {e}")
        finally:
            conn.close()


    @commands.command(name="view_availability")
    async def view_availability(self, ctx, player_name: str = None):
        """
        Command to view availability for a specific player or all players.
        Usage: !view_availability [player_name]
        """
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            if player_name:
                # Fetch availability for a specific player
                cursor.execute("""
                SELECT player_name, team, date, time_start, time_end
                FROM availability
                WHERE player_name = ?
                """, (player_name,))
            else:
                # Fetch availability for all players
                cursor.execute("""
                SELECT player_name, team, date, time_start, time_end
                FROM availability
                """)

            rows = cursor.fetchall()
            if rows:
                availability = "\n".join(
                    f"{row[0]} ({row[1]}) - {row[2]} from {row[3]} to {row[4]}" for row in rows
                )
                await ctx.send(f"📅 Player Availability:\n{availability}")
            else:
                await ctx.send("No availability records found.")
        except Exception as e:
            await ctx.send(f"❌ Failed to retrieve availability: {e}")
        finally:
            conn.close()


    @commands.command(name="clear_availability")
    async def clear_availability(self, ctx):
        """
        Command to clear a player's availability.
        Usage: !clear_availability
        """
        player_name = ctx.author.name

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            UPDATE availability
            SET date = NULL, time_start = NULL, time_end = NULL
            WHERE player_name = ?
            """, (player_name,))
            conn.commit()

            if cursor.rowcount > 0:
                await ctx.send(f"✅ Cleared availability for {player_name}.")
            else:
                await ctx.send(f"⚠️ No record found for {player_name}.")
        except Exception as e:
            await ctx.send(f"❌ Failed to clear availability: {e}")
        finally:
            conn.close()


    @commands.command(name="view_team")
    async def view_team(self, ctx, team_name: str):
        """View availability for a specific team."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            SELECT player_name, date, time_start, time_end
            FROM availability
            WHERE team = ?
            """, (team_name,))
            rows = cursor.fetchall()
            if rows:
                availability = "\n".join(
                    f"{row[0]} - {row[1]} from {row[2]} to {row[3]}" for row in rows
                )
                await ctx.send(f"📅 Availability for team {team_name}:\n{availability}")
            else:
                await ctx.send(f"No availability records found for team {team_name}.")
        except Exception as e:
            await ctx.send(f"❌ Failed to retrieve team availability: {e}")
        finally:
            conn.close()
