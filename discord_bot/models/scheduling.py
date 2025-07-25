# models/scheduling.py - Updated with PostgreSQL support
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import itertools

Base = declarative_base()

from collections import defaultdict

class SchedulingSession(Base):
    __tablename__ = 'scheduling_sessions'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, unique=True, index=True)
    team1 = Column(String)
    team2 = Column(String)
    player_schedules = Column(JSON)  # Store as JSON
    expected_players = Column(Integer, default=6)
    created_at = Column(DateTime, default=datetime.now)
    schedule_dates = Column(JSON)  # Store the date info
    confirmations = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    proposed_times = Column(JSON, default=[]) # New column to store proposed times

    def __init__(self, channel_id, team1, team2, player_schedules=None, expected_players=6, schedule_dates=None, confirmations=None, proposed_times=None):
        self.channel_id = str(channel_id)
        self.team1 = team1
        self.team2 = team2
        self.player_schedules = player_schedules if player_schedules is not None else {}
        self.expected_players = expected_players
        self.schedule_dates = schedule_dates if schedule_dates is not None else self.generate_next_week()
        self.confirmations = confirmations if confirmations is not None else {}
        self.proposed_times = proposed_times if proposed_times is not None else []
        self.created_at = datetime.now()
        self.is_active = True

    @property
    def teams(self):
        """Returns team1 and team2 as a list."""
        return [self.team1, self.team2]

    def generate_next_week(self):
        """Generate the next 7 days starting from current day"""
        dates = []
        start_date = datetime.now()
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            dates.append({
                'day_name': current_date.strftime('%A'),  # Monday, Tuesday, etc.
                'date': current_date.strftime('%m/%d'),    # 06/29
                'full_date': current_date.strftime('%A, %B %d'),  # Monday, June 29
            })
        return dates

    def get_date_info(self, day_name):
        """Get date info for a specific day name"""
        for date_info in self.schedule_dates:
            if date_info['day_name'] == day_name:
                return date_info
        return None

    def is_complete(self):
        return len(self.player_schedules) >= self.expected_players

    def find_common_times(self, min_players=None):
        if min_players is None:
            min_players = self.expected_players

        if not self.player_schedules or len(self.player_schedules) < min_players:
            return None

        common_times_result = defaultdict(list)
        player_ids = list(self.player_schedules.keys())

        # For each day of the week
        for date_info in self.schedule_dates:
            day_name = date_info['day_name']
            
            # Filter out players who have no availability on this day
            schedules_for_day = {
                uid: set(schedule.get(day_name, []))
                for uid, schedule in self.player_schedules.items()
                if schedule.get(day_name) # Ensure the list is not empty
            }

            if len(schedules_for_day) < min_players:
                continue

            # Generate combinations of players of the required size
            player_combinations = itertools.combinations(schedules_for_day.keys(), min_players)

            for combo in player_combinations:
                combo_schedules = [schedules_for_day[uid] for uid in combo]
                
                if not all(combo_schedules): # Skip if any player in combo has no times for the day
                    continue

                # Find intersection of times for the current combination
                intersection_of_times = set.intersection(*combo_schedules)
                
                # Filter out already proposed times for this day
                proposed_slots_for_day = {p['time'] for p in self.proposed_times if p['day'] == day_name}
                available_slots = sorted(list(intersection_of_times - proposed_slots_for_day))

                if available_slots:
                    # Identify the players NOT in this combination
                    odd_ones_out = list(set(player_ids) - set(combo))
                    
                    for time_slot in available_slots:
                        # Avoid proposing the same combination for the same time slot
                        is_duplicate = False
                        for existing_entry in common_times_result[day_name]:
                            if existing_entry['time'] == time_slot and set(existing_entry['players']) == set(combo):
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            common_times_result[day_name].append({
                                'time': time_slot,
                                'players': list(combo),
                                'excluded_players': odd_ones_out
                            })
        
        return dict(common_times_result) if common_times_result else None

    @classmethod
    def from_db(cls, db_session):
        """Create a SchedulingSession from database data"""
        session = cls(
            channel_id=int(db_session.channel_id),
            team1=db_session.team1,
            team2=db_session.team2,
            player_schedules=db_session.player_schedules or {},
            expected_players=db_session.expected_players,
            schedule_dates=db_session.schedule_dates or [],
            confirmations=db_session.confirmations or {},
            proposed_times=db_session.proposed_times or []
        )
        return session

def get_database_url():
    """Get database URL with PostgreSQL support and robust local fallback."""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # Default to a persistent SQLite database in the project's /data directory
        data_dir = ensure_data_directory()
        db_path = data_dir / "scheduling.db"
        print(f"💽 No DATABASE_URL env var found. Defaulting to SQLite at: {db_path}")
        return f'sqlite:///{db_path}'
    
    # Handle PostgreSQL URL format (DigitalOcean sometimes uses postgres://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url

def ensure_data_directory():
    """Ensure the data directory exists for SQLite, creating it if necessary."""
    try:
        # Assumes this file is in project_root/discord_bot/models/
        project_root = Path(__file__).resolve().parents[2]
        data_path = project_root / "data"
        data_path.mkdir(parents=True, exist_ok=True)
        print(f"[DB INFO] Data directory ensured at: {data_path}")
        return data_path
    except Exception as e:
        print(f"[DB WARNING] Could not create data directory: {e}. Using /tmp as fallback.")
        # Fallback for environments where this might fail
        tmp_path = Path("/tmp")
        tmp_path.mkdir(exist_ok=True)
        return tmp_path

def create_database_engine():
    """Create database engine with appropriate settings"""
    database_url = get_database_url()
    
    # print(f"🔗 Connecting to database: {database_url.split('@')[0]}@***" if '@' in database_url else database_url)
    
    if database_url.startswith('postgresql://'):
        # PostgreSQL settings
        engine = create_engine(
            database_url,
            pool_pre_ping=True,        # Verify connections before use
            pool_recycle=300,          # Recycle connections every 5 minutes
            pool_size=5,               # Connection pool size
            max_overflow=10,           # Max additional connections
            echo=False                 # Set to True for SQL debugging
        )
        print("[DB INFO] Using PostgreSQL with connection pooling")
    else:
        # SQLite settings
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=False
        )
        print("[DB INFO] Using SQLite database")
    
    return engine

# Database setup
try:
    engine = create_database_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    print("[DB INFO] Database tables created/verified")
except Exception as e:
    print(f"[DB ERROR] Database initialization error: {e}")
    # Fallback to in-memory SQLite for development
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    print("[DB WARNING] Using in-memory database as fallback")

def save_session(session_obj):
    """Save or update a scheduling session."""
    db = Session()
    try:
        channel_id = str(getattr(session_obj, 'channel_id', None))
        if not channel_id:
            print("[DB ERROR] session_obj missing channel_id")
            return None

        # Check if a session with this channel_id already exists
        existing_session_in_db = db.query(SchedulingSession).filter_by(channel_id=channel_id).first()

        if existing_session_in_db:
            # Update existing session's attributes explicitly
            existing_session_in_db.team1 = session_obj.team1
            existing_session_in_db.team2 = session_obj.team2
            existing_session_in_db.player_schedules = session_obj.player_schedules
            existing_session_in_db.expected_players = session_obj.expected_players
            existing_session_in_db.schedule_dates = session_obj.schedule_dates
            existing_session_in_db.confirmations = session_obj.confirmations
            existing_session_in_db.is_active = session_obj.is_active
            existing_session_in_db.proposed_times = session_obj.proposed_times
            db.add(existing_session_in_db) # Re-add to session to mark as dirty
            print(f"[DB INFO] Updating existing session for channel {channel_id}")
            merged_session = existing_session_in_db
        else:
            # Add new session
            db.add(session_obj)
            print(f"[DB INFO] Creating new session for channel {channel_id}")
            merged_session = session_obj # Use the new object for expunging

        db.commit()
        db.expunge(merged_session) # Detach the object from the session
        print(f"[DB SUCCESS] Session saved and detached for channel {channel_id}")
        return merged_session

    except Exception as e:
        db.rollback()
        print(f"[DB CRITICAL] CRITICAL: Error saving session for channel {getattr(session_obj, 'channel_id', 'UNKNOWN')}: {e}")
        raise
    finally:
        db.close()

def load_session(channel_id):
    """Load a scheduling session and detach it before returning."""
    db = Session()
    try:
        print(f"[DB INFO] Attempting to load session for channel {channel_id}")
        session_data = db.query(SchedulingSession).filter_by(
            channel_id=str(channel_id),
            is_active=True
        ).first()
        
        if session_data:
            # Detach the object from the session before returning
            db.expunge(session_data)
            print(f"[DB SUCCESS] Loaded and detached session for channel {channel_id}")
            return session_data
        else:
            print(f"[DB WARNING] No active session found for channel {channel_id}")
            return None
            
    except Exception as e:
        print(f"[DB CRITICAL] CRITICAL: Error loading session for channel {channel_id}: {e}")
        return None
    finally:
        db.close()

def delete_session(channel_id):
    """Mark a session as inactive with error handling"""
    db = Session()
    try:
        session_data = db.query(SchedulingSession).filter_by(
            channel_id=str(channel_id)
        ).first()
        if session_data:
            session_data.is_active = False
            db.commit()
            print(f"[DB INFO] Deactivated session for channel {channel_id}")
        else:
            print(f"[DB WARNING] No session found to delete for channel {channel_id}")
    except Exception as e:
        db.rollback()
        print(f"[DB ERROR] Error deleting session: {e}")
    finally:
        db.close()

def get_all_active_sessions():
    """Get all active sessions with error handling"""
    db = Session()
    try:
        sessions = db.query(SchedulingSession).filter_by(is_active=True).all()
        print(f"[DB INFO] Retrieved {len(sessions)} active sessions")
        return sessions
    except Exception as e:
        print(f"[DB ERROR] Error getting active sessions: {e}")
        return []
    finally:
        db.close()

def cleanup_old_sessions(days_old=7):
    """Clean up sessions older than specified days"""
    db = Session()
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)
        old_sessions = db.query(SchedulingSession).filter(
            SchedulingSession.created_at < cutoff_date,
            SchedulingSession.is_active == True
        ).all()
        
        for session in old_sessions:
            session.is_active = False
        
        db.commit()
        print(f"[DB INFO] Cleaned up {len(old_sessions)} old sessions")
        return len(old_sessions)
    except Exception as e:
        db.rollback()
        print(f"[DB ERROR] Error cleaning up old sessions: {e}")
        return 0
    finally:
        db.close()

def test_database_connection():
    """Test database connection and return status"""
    try:
        db = Session()
        db.execute(text("SELECT 1"))
        db.close()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

# Initialize and test connection
if __name__ == "__main__":
    success, message = test_database_connection()
    print(f"[DB TEST] {message}")