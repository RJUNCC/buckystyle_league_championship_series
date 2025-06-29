# models/scheduling.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os

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
    created_at = Column(DateTime, default=datetime.utcnow)
    schedule_dates = Column(JSON)  # Store the date info
    confirmations = Column(JSON, default={})
    is_active = Column(Boolean, default=True)

# Database setup
engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///scheduling.db'))
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def save_session(session_obj):
    """Save or update a scheduling session"""
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
        if session_obj.confirmations:
            for user_id, confirmed in session_obj.confirmations.items():
                confirmations_str[str(user_id)] = confirmed
        
        existing = db.query(SchedulingSession).filter_by(
            channel_id=str(session_obj.channel_id)
        ).first()
        
        if existing:
            existing.player_schedules = player_schedules_str
            existing.players_responded = players_responded_list
            existing.confirmations = confirmations_str
            existing.schedule_dates = session_obj.schedule_dates
            existing.team1 = session_obj.teams[0]
            existing.team2 = session_obj.teams[1]
        else:
            new_session = SchedulingSession(
                channel_id=str(session_obj.channel_id),
                team1=session_obj.teams[0],
                team2=session_obj.teams[1],
                player_schedules=player_schedules_str,
                players_responded=players_responded_list,
                expected_players=session_obj.expected_players,
                schedule_dates=session_obj.schedule_dates,
                confirmations=confirmations_str
            )
            db.add(new_session)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving session: {e}")
        raise
    finally:
        db.close()

def load_session(channel_id):
    """Load a scheduling session from database"""
    db = Session()
    try:
        session_data = db.query(SchedulingSession).filter_by(
            channel_id=str(channel_id),
            is_active=True
        ).first()
        return session_data
    finally:
        db.close()

def delete_session(channel_id):
    """Mark a session as inactive"""
    db = Session()
    try:
        session_data = db.query(SchedulingSession).filter_by(
            channel_id=str(channel_id)
        ).first()
        if session_data:
            session_data.is_active = False
            db.commit()
    except Exception as e:
        print(f"Error deleting session: {e}")
    finally:
        db.close()

def get_all_active_sessions():
    """Get all active sessions"""
    db = Session()
    try:
        return db.query(SchedulingSession).filter_by(is_active=True).all()
    finally:
        db.close()

def cleanup_old_sessions(days_old=7):
    """Clean up sessions older than specified days"""
    db = Session()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        old_sessions = db.query(SchedulingSession).filter(
            SchedulingSession.created_at < cutoff_date,
            SchedulingSession.is_active == True
        ).all()
        
        for session in old_sessions:
            session.is_active = False
        
        db.commit()
        return len(old_sessions)
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up old sessions: {e}")
        return 0
    finally:
        db.close()

# Import timedelta for cleanup function
from datetime import timedelta