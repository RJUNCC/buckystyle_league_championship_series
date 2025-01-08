# scheduling/database.py

import sqlite3

DB_NAME = "schedule.db"

def create_tables():
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
