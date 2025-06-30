# monitor_db.py
import time
import json
from models.scheduling import Session, SchedulingSession
from datetime import datetime

def monitor_sessions():
    while True:
        db = Session()
        try:
            sessions = db.query(SchedulingSession).filter_by(is_active=True).all()
            
            print(f"\n{'='*60}")
            print(f"Database Check at {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")
            
            if not sessions:
                print("No active sessions found")
            else:
                for session in sessions:
                    print(f"\nChannel: {session.channel_id}")
                    print(f"Teams: {session.team1} vs {session.team2}")
                    print(f"Players responded: {session.players_responded}")
                    
                    if session.player_schedules:
                        print("\nPlayer Schedules:")
                        schedules = json.loads(json.dumps(session.player_schedules))
                        for user_id, schedule in schedules.items():
                            print(f"  User {user_id}:")
                            for day, times in schedule.items():
                                if times:
                                    print(f"    {day}: {len(times)} slots - {times[:3]}...")
                                else:
                                    print(f"    {day}: Not available")
                    
                    print(f"\nConfirmations: {session.confirmations}")
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            db.close()
        
        time.sleep(5)  # Check every 5 seconds

if __name__ == "__main__":
    print("Monitoring scheduling database... Press Ctrl+C to stop")
    try:
        monitor_sessions()
    except KeyboardInterrupt:
        print("\nStopped monitoring")