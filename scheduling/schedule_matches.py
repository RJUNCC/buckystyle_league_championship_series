import pandas as pd
import sqlite3
from scheduling.database import DB_NAME

def load_team_stats(file_path="data/parquet/season_3_team_data.parquet"):
    """Load team stats from the saved Parquet file."""
    try:
        team_stats = pd.read_parquet(file_path)
        print("Team stats loaded successfully.")
        return team_stats
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None

def validate_teams(team1, team2, team_stats):
    """Validate that both teams are present in the team stats."""
    if team1 not in team_stats["Team"].values:
        print(f"Error: Team {team1} not found in the stats.")
        return False
    if team2 not in team_stats["Team"].values:
        print(f"Error: Team {team2} not found in the stats.")
        return False
    return True

def find_overlap(team1_slots, team2_slots):
    """Find overlapping time slots between two teams."""
    overlaps = []
    for t1 in team1_slots:
        for t2 in team2_slots:
            if t1[0] == t2[0]:  # Match dates
                start = max(t1[1], t2[1])
                end = min(t1[2], t2[2])
                if start < end:  # Valid overlap
                    overlaps.append((t1[0], start, end))
    return overlaps

def schedule_match(team1, team2):
    """Schedules a match between two teams."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Fetch availability for both teams
    cursor.execute("""
    SELECT player_name, date, time_start, time_end
    FROM availability
    WHERE team = ?
    """, (team1,))
    team1_slots = cursor.fetchall()

    cursor.execute("""
    SELECT player_name, date, time_start, time_end
    FROM availability
    WHERE team = ?
    """, (team2,))
    team2_slots = cursor.fetchall()

    # Find overlapping time slots
    overlaps = []
    for t1 in team1_slots:
        for t2 in team2_slots:
            if t1[1] == t2[1]:  # Match dates
                start = max(t1[2], t2[2])
                end = min(t1[3], t2[3])
                if start < end:  # Valid overlap
                    overlaps.append((t1[1], start, end))

    if overlaps:
        # Schedule the match in the first available slot
        match_date, match_start, match_end = overlaps[0]
        cursor.execute("""
        INSERT INTO matches (team1, team2, date, time_slot, status)
        VALUES (?, ?, ?, ?, 'Scheduled')
        """, (team1, team2, match_date, f"{match_start} - {match_end}"))

        conn.commit()
        conn.close()
        return f"✅ Match scheduled between {team1} and {team2} on {match_date} from {match_start} to {match_end}."
    else:
        conn.close()
        return f"⚠️ No overlapping availability found for {team1} and {team2}."


async def notify_players_for_availability(bot, team1, team2, channel_id):
    """Notify players to update availability via Discord."""
    channel = bot.get_channel(channel_id)
    if not channel:
        print(f"Error: Channel ID {channel_id} not found.")
        return

    await channel.send(
        f"⚠️ No overlapping availability found for {team1} vs {team2}. "
        "Players, please update your availability."
    )

async def retry_failed_scheduling():
    """Retry scheduling for matches with a 'Failed' status."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT team1, team2
    FROM matches
    WHERE status = 'Failed: No overlap'
    """)
    failed_matches = cursor.fetchall()

    for team1, team2 in failed_matches:
        print(f"Retrying scheduling for {team1} vs {team2}...")
        result = schedule_match(team1, team2)
        if result:
            print(f"Match successfully rescheduled for {team1} vs {team2}.")

    conn.close()
