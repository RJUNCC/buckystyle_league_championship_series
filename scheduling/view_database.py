import sqlite3

DB_NAME = "schedule.db"  # Replace with your actual database file name

def list_tables():
    """List all tables in the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    if tables:
        print("Tables in the database:")
        for table in tables:
            print(f"- {table[0]}")
    else:
        print("No tables found in the database.")

    conn.close()
    return [table[0] for table in tables]

def view_table(table_name):
    """View all data in the specified table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()

        if rows:
            print(f"\nData in table '{table_name}':")
            for row in rows:
                print(row)
        else:
            print(f"No data found in table '{table_name}'.")
    except sqlite3.OperationalError as e:
        print(f"Error accessing table '{table_name}': {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # List all tables
    tables = list_tables()

    if tables:
        # Prompt user to view a specific table
        table_to_view = input("\nEnter the table name to view its data (or press Enter to skip): ").strip()
        if table_to_view:
            view_table(table_to_view)
