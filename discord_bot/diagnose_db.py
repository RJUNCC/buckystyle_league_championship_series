
# diagnose_db.py
import asyncio
from models.database_config import initialize_database, get_session
from models.scheduling import SchedulingSession

async def inspect_database():
    """Connects to the database and prints all session records."""
    print("--- Database Inspection Tool ---")
    try:
        # Initialize the database connection
        initialize_database()
        db_session = get_session()
        print("✅ Database connection successful.")

        # Query for ALL sessions, regardless of is_active status
        all_sessions = db_session.query(SchedulingSession).all()

        if not all_sessions:
            print("❌ No sessions found in the database.")
            return

        print(f"Found {len(all_sessions)} total session(s) in the database:")
        for i, session in enumerate(all_sessions):
            print(f"--- Session #{i+1} ---")
            print(f"  Channel ID: {session.channel_id}")
            print(f"  Team 1: {session.team1}")
            print(f"  Team 2: {session.team2}")
            print(f"  Is Active: {session.is_active}")
            print(f"  Created At: {session.created_at}")
            print(f"  Players Responded: {len(session.players_responded or [])}")
        
    except Exception as e:
        print(f"❌ An error occurred during database inspection: {e}")
    finally:
        if 'db_session' in locals() and db_session:
            db_session.close()
            print("✅ Database session closed.")

if __name__ == "__main__":
    asyncio.run(inspect_database())
