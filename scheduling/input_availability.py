import sqlite3
from scheduling.database import DB_NAME

def add_availability(player_name, team, date, time_start, time_end):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO availability (player_name, team, date, time_start, time_end)
    VALUES (?, ?, ?, ?, ?)
    """, (player_name, team, date, time_start, time_end))

    conn.commit()
    conn.close()
    print(f"Availability added for {player_name} on {date} from {time_start} to {time_end}.")