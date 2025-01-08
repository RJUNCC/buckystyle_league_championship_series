import sqlite3
import pandas as pd
from config.config import Config

config = Config()

# File paths
team_file = f"data/parquet/{config.all_team_data}.parquet"
player_file = f"data/parquet/{config.all_player_data}.parquet"
DB_NAME = "schedule.db"

def create_tables():
    """Ensure required tables exist in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create Availability table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT NOT NULL,
        team TEXT NOT NULL,
        date TEXT,
        time_start TEXT,
        time_end TEXT
    )
    """)

    # Check if the columns allow NULLs and alter them if needed
    cursor.execute("PRAGMA table_info(availability);")
    columns = {col[1]: col[3] for col in cursor.fetchall()}  # col[3] is 'NOT NULL'

    if columns.get("date") == 1 or columns.get("time_start") == 1 or columns.get("time_end") == 1:
        print("Altering 'availability' table to allow NULLs for date, time_start, and time_end...")
        # Create a temporary table with updated schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability_temp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            team TEXT NOT NULL,
            date TEXT,
            time_start TEXT,
            time_end TEXT
        )
        """)
        # Copy existing data
        cursor.execute("""
        INSERT INTO availability_temp (id, player_name, team, date, time_start, time_end)
        SELECT id, player_name, team, date, time_start, time_end
        FROM availability;
        """)
        # Drop the old table and rename the temporary table
        cursor.execute("DROP TABLE availability;")
        cursor.execute("ALTER TABLE availability_temp RENAME TO availability;")
        print("Schema updated successfully.")

    # Create Matches table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team1 TEXT NOT NULL,
        team2 TEXT NOT NULL,
        date TEXT,
        time_slot TEXT,
        status TEXT DEFAULT 'Pending'
    )
    """)

    conn.commit()
    conn.close()

def insert_team_data():
    """Insert team-specific metrics into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # Load team data if still relevant for specific metrics
        team_data = pd.read_parquet(team_file)
        if "Team" not in team_data.columns:
            raise ValueError("Missing required column: 'Team'.")

        for _, row in team_data.iterrows():
            print(f"Team-specific data for {row['Team']} can be handled here.")
    except Exception as e:
        print(f"Error loading or handling team data: {e}")
    finally:
        conn.close()

def insert_player_data():
    """Insert player data (including team info) into the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # Load the updated player data
        player_data = pd.read_parquet(player_file)
        if "Player" not in player_data.columns or "Team" not in player_data.columns:
            raise ValueError("Missing required columns: 'Player' and 'Team'.")

        # Insert player data into the availability table
        for _, row in player_data.iterrows():
            cursor.execute("""
            INSERT INTO availability (player_name, team, date, time_start, time_end)
            VALUES (?, ?, NULL, NULL, NULL)
            """, (row["Player"], row["Team"]))
        conn.commit()
        print("Player data (with team info) inserted successfully.")
    except Exception as e:
        print(f"Error loading or inserting player data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
    insert_team_data()
    insert_player_data()
    print("Team and player data successfully inserted into the database.")
