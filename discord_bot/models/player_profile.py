# File: discord_bot/models/player_profile.py (ENHANCED VERSION)

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Use same database setup as scheduling
from models.scheduling import engine, Session

Base = declarative_base()

class PlayerProfile(Base):
    __tablename__ = 'player_profiles'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String, unique=True, index=True)  # Discord user ID
    discord_username = Column(String)  # Discord display name
    
    # Rocket League identifiers
    rl_name = Column(String)  # In-game name
    steam_id = Column(String)  # Steam ID for ballchasing.com
    epic_id = Column(String)  # Epic Games ID
    ballchasing_player_id = Column(String)  # ballchasing.com player ID
    
    # Profile customization (like hockey card info)
    custom_title = Column(String)  # Custom title like "Team Captain"
    favorite_car = Column(String)  # Octane, Dominus, etc.
    rank_name = Column(String)  # Champion, Grand Champion, etc.
    rank_division = Column(String)  # I, II, III, IV
    mmr = Column(Integer)  # Current MMR
    age = Column(Integer)  # Player age (like hockey cards)
    
    # Basic stats (updated from ballchasing.com)
    total_goals = Column(Integer, default=0)
    total_saves = Column(Integer, default=0)
    total_shots = Column(Integer, default=0)
    total_score = Column(Integer, default=0)
    total_assists = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    
    # Advanced stats (percentages like the hockey card)
    goal_percentage = Column(Float, default=0.0)  # Goals/Shots
    save_percentage = Column(Float, default=0.0)  # Saves/Shots Against
    win_percentage = Column(Float, default=0.0)   # Wins/Games
    
    # Additional tracked stats
    mvp_count = Column(Integer, default=0)  # MVP performances
    demos_inflicted = Column(Integer, default=0)  # Demos given
    demos_taken = Column(Integer, default=0)  # Demos received
    
    # League-specific stats
    season_goals = Column(Integer, default=0)
    season_saves = Column(Integer, default=0)
    season_wins = Column(Integer, default=0)
    season_games = Column(Integer, default=0)
    current_season = Column(String, default="Season 1")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    last_game_date = Column(DateTime)
    
    # Profile settings
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)  # Allow others to view profile
    
    # Additional data (JSON for flexibility)
    extra_data = Column(JSON)  # Store additional stats, achievements, etc.

# Create the table
Base.metadata.create_all(engine)

# Helper functions
def get_player_profile(discord_id):
    """Get player profile by Discord ID"""
    session = Session()
    try:
        profile = session.query(PlayerProfile).filter_by(
            discord_id=str(discord_id),
            is_active=True
        ).first()
        return profile
    finally:
        session.close()

def create_or_update_profile(discord_id, **kwargs):
    """Create or update a player profile"""
    session = Session()
    try:
        profile = session.query(PlayerProfile).filter_by(
            discord_id=str(discord_id)
        ).first()
        
        if profile:
            # Update existing profile
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.last_updated = datetime.utcnow()
        else:
            # Create new profile
            profile = PlayerProfile(
                discord_id=str(discord_id),
                **kwargs
            )
            session.add(profile)
        
        session.commit()
        return profile
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def update_player_stats(discord_id, stats_data):
    """Update player stats from ballchasing.com data"""
    session = Session()
    try:
        profile = session.query(PlayerProfile).filter_by(
            discord_id=str(discord_id)
        ).first()
        
        if profile:
            # Update stats
            profile.total_goals += stats_data.get('goals', 0)
            profile.total_saves += stats_data.get('saves', 0)
            profile.total_shots += stats_data.get('shots', 0)
            profile.total_score += stats_data.get('score', 0)
            profile.total_assists += stats_data.get('assists', 0)
            profile.games_played += 1
            
            # Update advanced stats
            if stats_data.get('mvp', False):
                profile.mvp_count += 1
            
            profile.demos_inflicted += stats_data.get('demos_inflicted', 0)
            profile.demos_taken += stats_data.get('demos_taken', 0)
            
            # Update season stats
            profile.season_goals += stats_data.get('goals', 0)
            profile.season_saves += stats_data.get('saves', 0)
            profile.season_games += 1
            
            if stats_data.get('won', False):
                profile.wins += 1
                profile.season_wins += 1
            else:
                profile.losses += 1
            
            # Calculate percentages
            if profile.total_shots > 0:
                profile.goal_percentage = (profile.total_goals / profile.total_shots) * 100
            
            if profile.games_played > 0:
                profile.win_percentage = (profile.wins / profile.games_played) * 100
            
            profile.last_updated = datetime.utcnow()
            profile.last_game_date = datetime.utcnow()
            
            session.commit()
            return profile
            
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_profiles():
    """Get all active player profiles"""
    session = Session()
    try:
        profiles = session.query(PlayerProfile).filter_by(
            is_active=True,
            is_public=True
        ).all()
        return profiles
    finally:
        session.close()

def search_profiles(search_term):
    """Search profiles by Discord username or RL name"""
    session = Session()
    try:
        profiles = session.query(PlayerProfile).filter(
            PlayerProfile.is_active == True,
            PlayerProfile.is_public == True
        ).filter(
            (PlayerProfile.discord_username.ilike(f'%{search_term}%')) |
            (PlayerProfile.rl_name.ilike(f'%{search_term}%'))
        ).all()
        return profiles
    finally:
        session.close()

def get_top_players_by_stat(stat_name, limit=10, min_games=5):
    """Get top players for a specific stat"""
    session = Session()
    try:
        query = session.query(PlayerProfile).filter(
            PlayerProfile.is_active == True,
            PlayerProfile.is_public == True,
            PlayerProfile.games_played >= min_games
        )
        
        if stat_name == 'goals':
            query = query.order_by(PlayerProfile.total_goals.desc())
        elif stat_name == 'saves':
            query = query.order_by(PlayerProfile.total_saves.desc())
        elif stat_name == 'wins':
            query = query.order_by(PlayerProfile.wins.desc())
        elif stat_name == 'win_percentage':
            query = query.order_by(PlayerProfile.win_percentage.desc())
        elif stat_name == 'goal_percentage':
            query = query.order_by(PlayerProfile.goal_percentage.desc())
        elif stat_name == 'mvp_rate':
            # Calculate MVP rate on the fly
            query = query.all()
            query = sorted(query, key=lambda p: (p.mvp_count / p.games_played) * 100 if p.games_played > 0 else 0, reverse=True)
            return query[:limit]
        
        return query.limit(limit).all()
    finally:
        session.close()

def reset_season_stats(season_name):
    """Reset all players' season stats for a new season"""
    session = Session()
    try:
        profiles = session.query(PlayerProfile).filter_by(is_active=True).all()
        
        for profile in profiles:
            profile.season_goals = 0
            profile.season_saves = 0
            profile.season_wins = 0
            profile.season_games = 0
            profile.current_season = season_name
            profile.last_updated = datetime.utcnow()
        
        session.commit()
        return len(profiles)
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()