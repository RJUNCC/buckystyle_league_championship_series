# File: discord_bot/models/player_profile.py (UPDATED FOR POSTGRESQL)

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import logging
from models.database_config import Base, get_session

logger = logging.getLogger(__name__)

class PlayerProfile(Base):
    __tablename__ = 'player_profiles'
    
    # Primary key - use UUID for PostgreSQL, Integer for SQLite
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Discord identifiers - BigInteger for Discord IDs (they're very large)
    discord_id = Column(BigInteger, unique=True, index=True, nullable=False)
    discord_username = Column(String(255))
    
    # Rocket League identifiers
    rl_name = Column(String(255))
    steam_id = Column(String(255))
    epic_id = Column(String(255))
    ballchasing_player_id = Column(String(255))
    ballchasing_platform = Column(String(50))  # steam, epic, etc.
    
    # Profile customization
    custom_title = Column(String(255))
    favorite_car = Column(String(100))
    rank_name = Column(String(100))
    rank_division = Column(String(10))
    mmr = Column(Integer)
    age = Column(Integer)
    
    # Basic stats (from ballchasing.com or manual entry)
    total_goals = Column(Integer, default=0, nullable=False)
    total_saves = Column(Integer, default=0, nullable=False)
    total_shots = Column(Integer, default=0, nullable=False)
    total_score = Column(BigInteger, default=0, nullable=False)  # Can be very large
    total_assists = Column(Integer, default=0, nullable=False)
    games_played = Column(Integer, default=0, nullable=False)
    wins = Column(Integer, default=0, nullable=False)
    losses = Column(Integer, default=0, nullable=False)
    
    # Calculated percentages
    goal_percentage = Column(Float, default=0.0, nullable=False)
    save_percentage = Column(Float, default=0.0, nullable=False)
    win_percentage = Column(Float, default=0.0, nullable=False)
    
    # Advanced stats
    mvp_count = Column(Integer, default=0, nullable=False)
    demos_inflicted = Column(Integer, default=0, nullable=False)
    demos_taken = Column(Integer, default=0, nullable=False)
    avg_speed = Column(Float, default=0.0, nullable=False)
    
    # BLCS-specific stats
    dominance_quotient = Column(Float, default=50.0, nullable=False)
    percentile_rank = Column(Float, default=50.0, nullable=False)
    
    # Season tracking
    season_goals = Column(Integer, default=0, nullable=False)
    season_saves = Column(Integer, default=0, nullable=False)
    season_wins = Column(Integer, default=0, nullable=False)
    season_games = Column(Integer, default=0, nullable=False)
    current_season = Column(String(100), default="BLCS 4")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_game_date = Column(DateTime)
    last_sync_date = Column(DateTime)  # When stats were last synced from ballchasing
    
    # Profile settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)
    
    # Additional data (JSON for flexibility)
    extra_data = Column(JSON)
    
    def __repr__(self):
        return f"<PlayerProfile(discord_id={self.discord_id}, rl_name='{self.rl_name}', games={self.games_played})>"
    
    def calculate_per_game_stats(self):
        """Calculate per-game statistics"""
        if self.games_played == 0:
            return {
                'goals_per_game': 0.0,
                'assists_per_game': 0.0,
                'saves_per_game': 0.0,
                'shots_per_game': 0.0,
                'score_per_game': 0.0,
                'demos_inflicted_per_game': 0.0,
                'demos_taken_per_game': 0.0
            }
        
        return {
            'goals_per_game': self.total_goals / self.games_played,
            'assists_per_game': self.total_assists / self.games_played,
            'saves_per_game': self.total_saves / self.games_played,
            'shots_per_game': self.total_shots / self.games_played,
            'score_per_game': self.total_score / self.games_played,
            'demos_inflicted_per_game': self.demos_inflicted / self.games_played,
            'demos_taken_per_game': self.demos_taken / self.games_played
        }
    
    def update_percentages(self):
        """Update calculated percentages, handling None values gracefully."""
        # Ensure numeric types are not None before comparing
        total_goals = self.total_goals or 0
        total_shots = self.total_shots or 0
        wins = self.wins or 0
        games_played = self.games_played or 0

        # Goal percentage
        if total_shots > 0:
            self.goal_percentage = (total_goals / total_shots) * 100
        else:
            self.goal_percentage = 0.0
        
        # Win percentage
        if games_played > 0:
            self.win_percentage = (wins / games_played) * 100
        else:
            self.win_percentage = 0.0
        
        # Update timestamp
        self.last_updated = datetime.utcnow()

# Helper functions with proper session management
def get_player_profile(discord_id):
    """Get player profile by Discord ID"""
    session = get_session()
    try:
        profile = session.query(PlayerProfile).filter_by(
            discord_id=int(discord_id),
            is_active=True
        ).first()
        return profile
    except Exception as e:
        logger.error(f"Error getting player profile {discord_id}: {e}")
        return None
    finally:
        session.close()

def create_or_update_profile(discord_id, **kwargs):
    """Create or update a player profile"""
    session = get_session()
    try:
        profile = session.query(PlayerProfile).filter_by(
            discord_id=int(discord_id)
        ).first()
        
        if profile:
            # Update existing profile
            for key, value in kwargs.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)
            profile.last_updated = datetime.utcnow()
            logger.info(f"Updated profile for Discord ID {discord_id}")
        else:
            # Create new profile
            profile = PlayerProfile(
                discord_id=int(discord_id),
                **kwargs
            )
            session.add(profile)
            logger.info(f"Created new profile for Discord ID {discord_id}")
        
        # Update calculated percentages
        profile.update_percentages()
        
        session.commit()
        session.refresh(profile)  # Load the latest data before the session closes
        return profile
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating/updating profile {discord_id}: {e}")
        raise e
    finally:
        session.close()

def update_player_stats_from_ballchasing(discord_id, ballchasing_stats):
    """Update player stats from ballchasing.com data"""
    session = get_session()
    try:
        profile = session.query(PlayerProfile).filter_by(
            discord_id=int(discord_id)
        ).first()
        
        if not profile:
            # Create new profile with ballchasing data
            profile = PlayerProfile(
                discord_id=int(discord_id),
                rl_name=ballchasing_stats.get('name', ''),
                ballchasing_platform=ballchasing_stats.get('platform', ''),
                **ballchasing_stats
            )
            session.add(profile)
            logger.info(f"Created new profile from ballchasing data for {discord_id}")
        else:
            # Update existing profile
            for key, value in ballchasing_stats.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)
            logger.info(f"Updated profile from ballchasing data for {discord_id}")
        
        # Update calculated fields
        profile.update_percentages()
        profile.last_sync_date = datetime.utcnow()
        
        session.commit()
        return profile
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating stats for {discord_id}: {e}")
        raise e
    finally:
        session.close()

def get_all_profiles():
    """Get all active player profiles"""
    session = get_session()
    try:
        profiles = session.query(PlayerProfile).filter_by(
            is_active=True,
            is_public=True
        ).order_by(PlayerProfile.games_played.desc()).all()
        return profiles
    except Exception as e:
        logger.error(f"Error getting all profiles: {e}")
        return []
    finally:
        session.close()

def search_profiles(search_term):
    """Search profiles by Discord username or RL name"""
    session = get_session()
    try:
        profiles = session.query(PlayerProfile).filter(
            PlayerProfile.is_active == True,
            PlayerProfile.is_public == True
        ).filter(
            (PlayerProfile.discord_username.ilike(f'%{search_term}%')) |
            (PlayerProfile.rl_name.ilike(f'%{search_term}%'))
        ).all()
        return profiles
    except Exception as e:
        logger.error(f"Error searching profiles: {e}")
        return []
    finally:
        session.close()

def get_top_players_by_stat(stat_name, limit=10, min_games=5):
    """Get top players for a specific stat"""
    session = get_session()
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
        elif stat_name == 'dominance_quotient':
            query = query.order_by(PlayerProfile.dominance_quotient.desc())
        else:
            # Default to games played
            query = query.order_by(PlayerProfile.games_played.desc())
        
        return query.limit(limit).all()
        
    except Exception as e:
        logger.error(f"Error getting top players: {e}")
        return []
    finally:
        session.close()

def reset_season_stats(season_name):
    """Reset all players' season stats for a new season"""
    session = get_session()
    try:
        updated_count = session.query(PlayerProfile).filter_by(
            is_active=True
        ).update({
            PlayerProfile.season_goals: 0,
            PlayerProfile.season_saves: 0,
            PlayerProfile.season_wins: 0,
            PlayerProfile.season_games: 0,
            PlayerProfile.current_season: season_name,
            PlayerProfile.last_updated: datetime.utcnow()
        })
        
        session.commit()
        logger.info(f"Reset season stats for {updated_count} players")
        return updated_count
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error resetting season stats: {e}")
        raise e
    finally:
        session.close()

def get_database_stats():
    """Get database statistics for admin purposes"""
    session = get_session()
    try:
        total_profiles = session.query(PlayerProfile).count()
        active_profiles = session.query(PlayerProfile).filter_by(is_active=True).count()
        profiles_with_games = session.query(PlayerProfile).filter(PlayerProfile.games_played > 0).count()
        
        # Most recent activity
        latest_update = session.query(PlayerProfile.last_updated).order_by(
            PlayerProfile.last_updated.desc()
        ).first()
        
        latest_sync = session.query(PlayerProfile.last_sync_date).filter(
            PlayerProfile.last_sync_date.isnot(None)
        ).order_by(PlayerProfile.last_sync_date.desc()).first()
        
        return {
            'total_profiles': total_profiles,
            'active_profiles': active_profiles,
            'profiles_with_games': profiles_with_games,
            'latest_update': latest_update[0] if latest_update else None,
            'latest_sync': latest_sync[0] if latest_sync else None
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {}
    finally:
        session.close()

# Legacy compatibility functions
def update_player_stats(discord_id, stats_data):
    """Legacy function - update player stats (compatibility)"""
    return update_player_stats_from_ballchasing(discord_id, stats_data)