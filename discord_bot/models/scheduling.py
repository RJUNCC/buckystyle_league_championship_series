# models/scheduling.py - Updated with PostgreSQL support
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

Base = declarative_base()

class SchedulingSession(Base):
    __tablename__ = 'scheduling_sessions'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, unique=True, index=True)
    team1 = Column(String)
    team2 = Column(String)
    player_schedules = Column(JSON)  # Store as JSON
    players_responded = Column(JSON)  # List of user IDs
    expected_players = Column(Integer, default=6)
    created_at = Column(DateTime, default=datetime.now)
    schedule_dates = Column(JSON)  # Store the date info
    confirmations = Column(JSON, default={})
    is_active = Column(Boolean, default=True)

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
        print(f"✅ Data directory ensured at: {data_path}")
        return data_path
    except Exception as e:
        print(f"⚠️ Warning: Could not create data directory: {e}. Using /tmp as fallback.")
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
        print("✅ Using PostgreSQL with connection pooling")
    else:
        # SQLite settings
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=False
        )
        print("✅ Using SQLite database")
    
    return engine

# Database setup
try:
    engine = create_database_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    print("✅ Database tables created/verified")
except Exception as e:
    print(f"❌ Database initialization error: {e}")
    # Fallback to in-memory SQLite for development
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    print("⚠️ Using in-memory database as fallback")

def save_session(session_obj):
    """Save or update a scheduling session with better error handling"""
    db = Session()
    try:
        # Convert sets to lists for JSON serialization
        players_responded_list = list(session_obj.players_responded) if hasattr(session_obj.players_responded, '__iter__') else []
        
        # Convert user IDs to strings for consistency
        player_schedules_str = {}
        if session_obj.player_schedules:
            for user_id, schedule in session_obj.player_schedules.items():
                player_schedules_str[str(user_id)] = schedule
        
        confirmations_str = {}
        if hasattr(session_obj, 'confirmations') and session_obj.confirmations:
            for user_id, confirmed in session_obj.confirmations.items():
                confirmations_str[str(user_id)] = confirmed
        
        existing = db.query(SchedulingSession).filter_by(
            channel_id=str(session_obj.channel_id)
        ).first()
        
        if existing:
            # Update existing session
            existing.player_schedules = player_schedules_str
            existing.players_responded = players_responded_list
            existing.confirmations = confirmations_str
            existing.schedule_dates = getattr(session_obj, 'schedule_dates', [])
            existing.team1 = session_obj.teams[0]
            existing.team2 = session_obj.teams[1]
            existing.expected_players = getattr(session_obj, 'expected_players', 6)
            print(f"📝 Updated session for channel {session_obj.channel_id}")
        else:
            # Create new session
            new_session = SchedulingSession(
                channel_id=str(session_obj.channel_id),
                team1=session_obj.teams[0],
                team2=session_obj.teams[1],
                player_schedules=player_schedules_str,
                players_responded=players_responded_list,
                expected_players=getattr(session_obj, 'expected_players', 6),
                schedule_dates=getattr(session_obj, 'schedule_dates', []),
                confirmations=confirmations_str
            )
            db.add(new_session)
            print(f"💾 Created new session for channel {session_obj.channel_id}")
        
        db.commit()
        print(f"✅ Session saved successfully to database")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving session: {e}")
        raise
    finally:
        db.close()

def load_session(channel_id):
    """Load a scheduling session from database with error handling"""
    db = Session()
    try:
        session_data = db.query(SchedulingSession).filter_by(
            channel_id=str(channel_id),
            is_active=True
        ).first()
        
        if session_data:
            print(f"📖 Loaded session for channel {channel_id}")
        
        return session_data
    except Exception as e:
        print(f"❌ Error loading session: {e}")
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
            print(f"🗑️ Deactivated session for channel {channel_id}")
        else:
            print(f"⚠️ No session found to delete for channel {channel_id}")
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting session: {e}")
    finally:
        db.close()

def get_all_active_sessions():
    """Get all active sessions with error handling"""
    db = Session()
    try:
        sessions = db.query(SchedulingSession).filter_by(is_active=True).all()
        print(f"📋 Retrieved {len(sessions)} active sessions")
        return sessions
    except Exception as e:
        print(f"❌ Error getting active sessions: {e}")
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
        print(f"🧹 Cleaned up {len(old_sessions)} old sessions")
        return len(old_sessions)
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning up old sessions: {e}")
        return 0
    finally:
        db.close()

def test_database_connection():
    """Test database connection and return status"""
    try:
        db = Session()
        db.execute("SELECT 1")
        db.close()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"

# Initialize and test connection
if __name__ == "__main__":
    success, message = test_database_connection()
    print(f"🔍 Database test: {message}")