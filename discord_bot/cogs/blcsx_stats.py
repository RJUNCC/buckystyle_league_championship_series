# cogs/blcsx_stats.py - Pure Py-cord Implementation
import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import json
import logging
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from omegaconf import OmegaConf
import numpy as np
import pandas as pd
from omegaconf import DictConfig, OmegaConf
import hydra

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, BigInteger
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.dialects.postgresql import insert
    SQLALCHEMY_AVAILABLE = True
    
    Base = declarative_base()
    
    class PlayerMapping(Base):
        __tablename__ = 'blcs_player_mappings'
        
        discord_id = Column(BigInteger, primary_key=True)
        discord_username = Column(String(255))
        ballchasing_player_id = Column(String(255))
        ballchasing_platform = Column(String(50))
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class PlayerStatistics(Base):
        __tablename__ = 'blcs_player_statistics'
        
        player_id = Column(String(255), primary_key=True)
        season_id = Column(String(255))
        games_played = Column(Integer)
        wins = Column(Integer)
        losses = Column(Integer)
        avg_score = Column(Float)
        goals_per_game = Column(Float)
        assists_per_game = Column(Float)
        saves_per_game = Column(Float)
        shots_per_game = Column(Float)
        shot_percentage = Column(Float)
        demos_inflicted_per_game = Column(Float)
        demos_taken_per_game = Column(Float)
        avg_speed = Column(Float)
        dominance_quotient = Column(Float)
        percentile_rank = Column(Float)
        last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy/psycopg2 not available - database features disabled")

class BallchasingAPI:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://ballchasing.com/api"
        self.headers = {"Authorization": api_token}
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_group_data(self, group_id: str) -> Dict:
        """Get comprehensive group data including all players and teams"""
        try:
            async with self.session.get(f"{self.base_url}/groups/{group_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get group data: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching group data: {e}")
            return {}

class SimpleMemoryStorage:
    """Simple in-memory storage when database is not available"""
    def __init__(self):
        self.player_mappings = {}
        self.player_stats = {}
    
    def add_player_mapping(self, discord_id: int, discord_username: str, 
                          ballchasing_player_id: str, platform: str):
        """Add or update player mapping"""
        self.player_mappings[discord_id] = {
            'discord_id': discord_id,
            'discord_username': discord_username,
            'ballchasing_player_id': ballchasing_player_id,
            'ballchasing_platform': platform
        }
        logger.info(f"Stored mapping for {discord_username}")
    
    def get_player_mapping(self, discord_id: int) -> Optional[Dict]:
        """Get player mapping by Discord ID"""
        return self.player_mappings.get(discord_id)
    
    def update_player_statistics(self, player_stats: Dict):
        """Update player statistics"""
        player_id = player_stats['player_id']
        self.player_stats[player_id] = player_stats
        logger.info(f"Updated stats for {player_id}")
    
    def get_player_statistics(self, player_id: str) -> Optional[Dict]:
        """Get player statistics"""
        return self.player_stats.get(player_id)
    
    def get_all_player_statistics(self) -> List[Dict]:
        """Get all player statistics for ranking calculations"""
        return list(self.player_stats.values())

class DatabaseManager:
    def __init__(self, database_url: str):
        if not SQLALCHEMY_AVAILABLE:
            logger.warning("Using memory storage - data will not persist")
            self.storage = SimpleMemoryStorage()
            self.use_db = False
            return
        
        try:
            self.engine = create_engine(database_url)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.Session = Session
            self.use_db = True
            logger.info("PostgreSQL database initialized for BLCS stats")
        except Exception as e:
            logger.warning(f"Database failed, using memory storage: {e}")
            self.storage = SimpleMemoryStorage()
            self.use_db = False
    
    def add_player_mapping(self, discord_id: int, discord_username: str, 
                          ballchasing_player_id: str, platform: str):
        """Add or update player mapping"""
        if not self.use_db:
            return self.storage.add_player_mapping(discord_id, discord_username, ballchasing_player_id, platform)
        
        try:
            with self.Session() as session:
                stmt = insert(PlayerMapping).values(
                    discord_id=discord_id,
                    discord_username=discord_username,
                    ballchasing_player_id=ballchasing_player_id,
                    ballchasing_platform=platform
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['discord_id'],
                    set_=dict(
                        discord_username=stmt.excluded.discord_username,
                        ballchasing_player_id=stmt.excluded.ballchasing_player_id,
                        ballchasing_platform=stmt.excluded.ballchasing_platform,
                        updated_at=datetime.utcnow()
                    )
                )
                session.execute(stmt)
                session.commit()
        except Exception as e:
            logger.error(f"Error saving player mapping: {e}")
    
    def get_player_mapping(self, discord_id: int) -> Optional[Dict]:
        """Get player mapping by Discord ID"""
        if not self.use_db:
            return self.storage.get_player_mapping(discord_id)
        
        try:
            with self.Session() as session:
                mapping = session.query(PlayerMapping).filter_by(discord_id=discord_id).first()
                if mapping:
                    return {
                        'discord_id': mapping.discord_id,
                        'discord_username': mapping.discord_username,
                        'ballchasing_player_id': mapping.ballchasing_player_id,
                        'ballchasing_platform': mapping.ballchasing_platform
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting player mapping: {e}")
            return None
    
    def update_player_statistics(self, player_stats: Dict):
        """Update player statistics"""
        if not self.use_db:
            return self.storage.update_player_statistics(player_stats)
        
        try:
            with self.Session() as session:
                logger.info(f"Attempting to update stats for player_id: {player_stats.get('player_id')}")
                stmt = insert(PlayerStatistics).values(**player_stats)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['player_id'],
                    set_={k: stmt.excluded[k] for k in player_stats.keys() if k != 'player_id'}
                )
                session.execute(stmt)
                session.commit()
                logger.info(f"Successfully updated stats for player_id: {player_stats.get('player_id')}")
        except Exception as e:
            logger.error(f"Error updating player statistics for {player_stats.get('player_id')}: {e}")
    
    def get_player_statistics(self, player_id: str) -> Optional[Dict]:
        """Get player statistics"""
        if not self.use_db:
            return self.storage.get_player_statistics(player_id)
        
        try:
            with self.Session() as session:
                logger.info(f"Attempting to retrieve stats for player_id: {player_id}")
                stats = session.query(PlayerStatistics).filter_by(player_id=player_id).first()
                if stats:
                    logger.info(f"Successfully retrieved stats for player_id: {player_id}")
                    return {
                        'player_id': stats.player_id,
                        'season_id': stats.season_id,
                        'games_played': stats.games_played,
                        'wins': stats.wins,
                        'losses': stats.losses,
                        'avg_score': stats.avg_score,
                        'goals_per_game': stats.goals_per_game,
                        'assists_per_game': stats.assists_per_game,
                        'saves_per_game': stats.saves_per_game,
                        'shots_per_game': stats.shots_per_game,
                        'shot_percentage': stats.shot_percentage,
                        'demos_inflicted_per_game': stats.demos_inflicted_per_game,
                        'demos_taken_per_game': stats.demos_taken_per_game,
                        'avg_speed': stats.avg_speed,
                        'dominance_quotient': stats.dominance_quotient,
                        'percentile_rank': stats.percentile_rank,
                        'last_updated': stats.last_updated
                    }
                logger.warning(f"No stats found for player_id: {player_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting player statistics for {player_id}: {e}")
            return None
    
    def get_all_player_statistics(self) -> List[Dict]:
        """Get all player statistics for ranking, joined with player names."""
        if not self.use_db:
            # Fallback for memory storage (less efficient)
            stats = self.storage.get_all_player_statistics()
            mappings = self.storage.player_mappings
            # Create a reverse map from ballchasing_id to discord_username
            reverse_map = {v['ballchasing_player_id']: v['discord_username'] for k, v in mappings.items()}
            for s in stats:
                s['discord_username'] = reverse_map.get(s['player_id'])
            return sorted(stats, key=lambda x: x.get('dominance_quotient', 0), reverse=True)

        try:
            with self.Session() as session:
                # Efficiently join PlayerStatistics with PlayerMapping
                results = (
                    session.query(PlayerStatistics, PlayerMapping.discord_username)
                    .outerjoin(PlayerMapping, PlayerStatistics.player_id == PlayerMapping.ballchasing_player_id)
                    .order_by(PlayerStatistics.dominance_quotient.desc())
                    .all()
                )
                
                # Process results into a list of dictionaries
                all_stats = []
                for stats, discord_username in results:
                    stat_dict = {
                        c.name: getattr(stats, c.name) for c in stats.__table__.columns
                    }
                    stat_dict['discord_username'] = discord_username
                    all_stats.append(stat_dict)
                
                return all_stats
        except Exception as e:
            logger.error(f"Error getting all player statistics: {e}")
            return []
    
    def get_all_player_mappings(self) -> List[Dict]:
        """Get all player mappings from the database"""
        if not self.use_db:
            return list(self.storage.player_mappings.values())

        try:
            with self.Session() as session:
                all_mappings = session.query(PlayerMapping).all()
                return [{
                    'discord_id': mapping.discord_id,
                    'discord_username': mapping.discord_username,
                    'ballchasing_player_id': mapping.ballchasing_player_id,
                    'ballchasing_platform': mapping.ballchasing_platform
                } for mapping in all_mappings]
        except Exception as e:
            logger.error(f"Error getting all player mappings: {e}")
            return []





class DataDrivenDominanceQuotientCalculator:
    def __init__(self):
        """
        Dominance Quotient calculator based on BLCS4 season analysis
        Designed to identify individual skill regardless of team performance
        """
        
        # Weights based on BLCS4 data analysis
        # Key insight: Individual stats matter WAY more than team luck
        self.stat_weights = {
            # Core individual performance (90% total weight)
            'avg_score': 0.40,              # Most important - overall game impact
            'saves_per_game': 0.25,         # Defensive skill highly valued
            'goals_per_game': 0.15,         # Offensive production
            'assists_per_game': 0.10,       # Playmaking/team support
            
            # Secondary performance indicators (5% total weight)
            'shooting_pct': 0.03,           # Efficiency over volume
            'shots_per_game': 0.02,         # Offensive pressure
            
            # Team success (5% total weight) - MINIMAL impact
            'win_rate': 0.05                # Proven to be mostly team luck
        }
        
        # Tournament adjustments based on Bo7 double elimination
        self.tournament_config = {
            'min_games_threshold': 8,        # Minimum possible games (0-4, 0-4)
            'early_elimination_threshold': 14,  # 8-14 games = early out
            'deep_run_threshold': 22,        # 22+ games = finals/winner
            'confidence_games': 16,          # Games needed for full win rate confidence
            
            # Opportunity adjustments
            'early_elimination_boost': 0.12,  # 12% boost for early elimination
            'deep_run_penalty': 0.06,        # 6% penalty for deep runs
        }
        
        # Performance thresholds based on BLCS4 data
        self.performance_benchmarks = {
            'elite_score_threshold': 450,     # Top tier like JERID (543), DESI (488)
            'good_score_threshold': 380,      # Above average performers
            'average_score_threshold': 320,   # League average range
            
            'elite_saves_threshold': 2.2,     # Defensive specialists like who Drose (2.45)
            'good_saves_threshold': 1.8,      # Above average defense
            
            'elite_goals_threshold': 1.1,     # Offensive threats like JERID (1.16)
            'good_goals_threshold': 0.8,      # Above average offense
        }
    
    def calculate_percentile(self, player_value: float, all_values: List[float], 
                           higher_is_better: bool = True) -> float:
        """Calculate what percentage of players this value beats"""
        if not all_values or len(all_values) <= 1:
            return 50.0
        
        # Filter out invalid values
        valid_values = [v for v in all_values if not pd.isna(v) and v is not None]
        if not valid_values:
            return 50.0
        
        if higher_is_better:
            better_count = sum(1 for v in valid_values if v < player_value)
        else:
            better_count = sum(1 for v in valid_values if v > player_value)
        
        return (better_count / len(valid_values)) * 100
    
    def get_tournament_adjustment_factor(self, games_played: int) -> float:
        """Calculate opportunity adjustment based on games played"""
        if games_played <= self.tournament_config['early_elimination_threshold']:
            # Early elimination: Fewer opportunities to showcase skill
            adjustment = 1.0 + self.tournament_config['early_elimination_boost']
            adjustment_type = "early elimination boost"
        elif games_played >= self.tournament_config['deep_run_threshold']:
            # Deep run: More opportunities to accumulate stats
            adjustment = 1.0 - self.tournament_config['deep_run_penalty']
            adjustment_type = "deep run penalty"
        else:
            # Standard tournament run
            adjustment = 1.0
            adjustment_type = "no adjustment"
        
        logger.info(f"Games: {games_played}, adjustment: {adjustment:.3f} ({adjustment_type})")
        return adjustment
    
    def calculate_skill_consistency_bonus(self, player_stats: Dict) -> float:
        """Bonus for players who excel in multiple areas"""
        score_tier = 0
        if player_stats.get('avg_score', 0) >= self.performance_benchmarks['elite_score_threshold']:
            score_tier = 3  # Elite
        elif player_stats.get('avg_score', 0) >= self.performance_benchmarks['good_score_threshold']:
            score_tier = 2  # Good
        elif player_stats.get('avg_score', 0) >= self.performance_benchmarks['average_score_threshold']:
            score_tier = 1  # Average
        
        # Check if player excels in multiple specific areas
        specialties = 0
        if player_stats.get('saves_per_game', 0) >= self.performance_benchmarks['elite_saves_threshold']:
            specialties += 1  # Defensive specialist
        if player_stats.get('goals_per_game', 0) >= self.performance_benchmarks['elite_goals_threshold']:
            specialties += 1  # Offensive threat
        if player_stats.get('assists_per_game', 0) >= 1.0:
            specialties += 1  # Playmaker
        
        # Multi-skilled players get a small bonus
        if score_tier >= 2 and specialties >= 2:
            return 1.05  # 5% bonus for well-rounded elite players
        elif score_tier >= 1 and specialties >= 1:
            return 1.02  # 2% bonus for solid specialists
        else:
            return 1.0   # No bonus
    
    def calculate_win_rate_with_context(self, player_stats: Dict, all_players: List[Dict]) -> float:
        """Calculate win rate percentile with heavy regression for small samples"""
        player_games = player_stats.get('games_played', 0)
        player_wins = player_stats.get('wins', 0)
        player_win_rate = player_wins / max(player_games, 1)
        
        # Calculate league averages
        total_wins = sum(p.get('wins', 0) for p in all_players)
        total_games = sum(p.get('games_played', 0) for p in all_players)
        league_avg_win_rate = total_wins / max(total_games, 1)
        
        # Heavy regression to mean for tournament play
        confidence_factor = min(player_games / self.tournament_config['confidence_games'], 1.0)
        
        # Blend individual win rate with league average
        adjusted_win_rate = (confidence_factor * player_win_rate) + \
                           ((1 - confidence_factor) * league_avg_win_rate)
        
        # Calculate percentile among all adjusted win rates
        all_adjusted_rates = []
        for p in all_players:
            p_games = p.get('games_played', 0)
            p_wins = p.get('wins', 0)
            p_win_rate = p_wins / max(p_games, 1)
            p_confidence = min(p_games / self.tournament_config['confidence_games'], 1.0)
            p_adjusted = (p_confidence * p_win_rate) + ((1 - p_confidence) * league_avg_win_rate)
            all_adjusted_rates.append(p_adjusted)
        
        percentile = self.calculate_percentile(adjusted_win_rate, all_adjusted_rates, True)
        
        logger.info(f"Win rate: {player_win_rate:.3f} -> {adjusted_win_rate:.3f} "
                   f"(confidence: {confidence_factor:.2f}, percentile: {percentile:.1f})")
        
        return percentile
    
    def calculate_dominance_quotient(self, player_stats: Dict, all_players: List[Dict]) -> float:
        """
        Calculate the Data-Driven Dominance Quotient
        Based on BLCS4 analysis showing individual stats >> team success
        """
        if not all_players:
            return 50.0
        
        player_name = player_stats.get('player_id', 'Unknown')
        logger.info(f"\n=== Calculating DQ for {player_name} ===")
        
        # Extract stat values for percentile calculations
        stat_lists = {}
        for stat_key in ['avg_score', 'goals_per_game', 'assists_per_game', 'saves_per_game', 
                        'shots_per_game', 'shot_percentage']: # Changed shooting_pct to shot_percentage
            stat_lists[stat_key] = [p.get(stat_key, 0) for p in all_players if p.get(stat_key) is not None]
        
        # Calculate percentiles for each stat
        percentiles = {}
        weighted_contributions = {}
        
        for stat_key, weight in self.stat_weights.items():
            if stat_key == 'win_rate':
                # Special handling for win rate
                percentiles[stat_key] = self.calculate_win_rate_with_context(player_stats, all_players)
            elif stat_key in stat_lists and stat_lists[stat_key]:
                player_value = player_stats.get(stat_key, 0)
                percentiles[stat_key] = self.calculate_percentile(player_value, stat_lists[stat_key], True)
            else:
                percentiles[stat_key] = 50.0  # Default if no data
            
            # Calculate weighted contribution
            weighted_contributions[stat_key] = percentiles[stat_key] * weight
            
            logger.info(f"{stat_key}: {player_stats.get(stat_key, 0):.2f} -> "
                       f"{percentiles[stat_key]:.1f}th percentile x {weight:.3f} = "
                       f"{weighted_contributions[stat_key]:.2f}")
        
        # Sum all weighted contributions
        base_dominance_quotient = sum(weighted_contributions.values())
        
        # Apply tournament opportunity adjustment
        games_played = player_stats.get('games_played', 0)
        tournament_factor = self.get_tournament_adjustment_factor(games_played)
        
        # Apply skill consistency bonus
        consistency_bonus = self.calculate_skill_consistency_bonus(player_stats)
        
        # Calculate final DQ
        final_dq = base_dominance_quotient * tournament_factor * consistency_bonus
        
        # Clamp to 0-100 range
        final_dq = max(0, min(100, final_dq))
        
        logger.info(f"Base DQ: {base_dominance_quotient:.2f}")
        logger.info(f"Tournament factor: {tournament_factor:.3f}")
        logger.info(f"Consistency bonus: {consistency_bonus:.3f}")
        logger.info(f"Final DQ: {final_dq:.1f}")
        
        return final_dq
    
    def analyze_player_profile(self, player_stats: Dict, all_players: List[Dict]) -> Dict:
        """Provide detailed analysis of a player's strengths and weaknesses"""
        analysis = {
            'dominance_quotient': self.calculate_dominance_quotient(player_stats, all_players),
            'player_type': '',
            'strengths': [],
            'weaknesses': [],
            'comparison_to_league': {}
        }
        
        # Determine player type based on stats
        avg_score = player_stats.get('avg_score', 0)
        saves_per_game = player_stats.get('saves_per_game', 0)
        goals_per_game = player_stats.get('goals_per_game', 0)
        win_rate = player_stats.get('wins', 0) / max(player_stats.get('games_played', 1), 1) * 100
        
        # Player type classification
        if avg_score >= self.performance_benchmarks['elite_score_threshold']:
            if win_rate >= 55:
                analysis['player_type'] = "Elite Carry (High skill + winning team)"
            else:
                analysis['player_type'] = "Elite Victim (High skill + bad team)"
        elif avg_score >= self.performance_benchmarks['good_score_threshold']:
            analysis['player_type'] = "Solid Contributor"
        elif win_rate >= 55:
            analysis['player_type'] = "Team Passenger (Carried by good team)"
        else:
            analysis['player_type'] = "Developing Player"
        
        # Identify strengths
        if saves_per_game >= self.performance_benchmarks['elite_saves_threshold']:
            analysis['strengths'].append("Elite Defender")
        if goals_per_game >= self.performance_benchmarks['elite_goals_threshold']:
            analysis['strengths'].append("Offensive Threat")
        if player_stats.get('assists_per_game', 0) >= 1.0:
            analysis['strengths'].append("Playmaker")
        if avg_score >= self.performance_benchmarks['elite_score_threshold']:
            analysis['strengths'].append("Overall Impact")
        
        return analysis

class BLCSXStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Check for required environment variables
        database_url = os.getenv('DATABASE_URL')
        ballchasing_token = os.getenv('BALLCHASING_API_KEY')
        
        if not database_url:
            logger.warning("DATABASE_URL not set - using fallback storage")
            database_url = 'sqlite:///:memory:'
        
        if not ballchasing_token:
            logger.warning("BALLCHASING_API_KEY not set - update features disabled")
        
        self.ballchasing_token = ballchasing_token
        self.db = DatabaseManager(database_url)
        
        self.calculator = DataDrivenDominanceQuotientCalculator()
        
        # Performance indicators (emojis removed as requested)
        self.performance_indicators = {
            'elite': {'threshold': 90, 'color': 0x4CAF50, 'name': 'ELITE'},
            'excellent': {'threshold': 80, 'color': 0x8BC34A, 'name': 'EXCELLENT'},
            'good': {'threshold': 65, 'color': 0xFFC107, 'name': 'GOOD'},
            'average': {'threshold': 35, 'color': 0xFF9800, 'name': 'AVERAGE'},
            'poor': {'threshold': 20, 'color': 0xF44336, 'name': 'POOR'},
            'terrible': {'threshold': 0, 'color': 0xB71C1C, 'name': 'TERRIBLE'}
        }
        
        logger.info("BLCSX Stats Cog initialized")

    def get_performance_indicator(self, percentile: float) -> Dict:
        """Get performance indicator based on percentile"""
        for level, data in self.performance_indicators.items():
            if percentile >= data['threshold']:
                return data
        return self.performance_indicators['terrible']

    @discord.slash_command(name="blcs_profile", description="Show comprehensive BLCSX player profile with rankings")
    async def profile_command(self, ctx, player: discord.Member = None):
        """Modern profile command with detailed rankings"""
        target_user = player or ctx.author
        
        await ctx.response.defer()
        
        try:
            # Get player mapping
            mapping = self.db.get_player_mapping(target_user.id)
            if not mapping:
                embed = discord.Embed(
                    title="Player Not Found",
                    description=f"No ballchasing.com mapping found for {target_user.display_name}.\nUse `/blcs_link` to connect your account.",
                    color=discord.Color.red()
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Get player statistics
            player_stats = self.db.get_player_statistics(mapping['ballchasing_player_id'])
            if not player_stats:
                embed = discord.Embed(
                    title="No Statistics",
                    description=f"No statistics found for {target_user.display_name}.\nData may still be processing.",
                    color=discord.Color.orange()
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Get all players for comparison
            all_players = self.db.get_all_player_statistics()
            
            # Generate modern profile embed
            embed = self.create_profile_embed(target_user, player_stats, all_players)
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in profile command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while generating the profile.",
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed)

    def create_profile_embed(self, user: discord.User, player_stats: Dict, all_players: List[Dict]) -> discord.Embed:
        """Create modern profile embed with rankings and indicators"""
        
        # Calculate win rate and basic stats
        win_rate = (player_stats['wins'] / max(player_stats['games_played'], 1)) * 100
        
        # Calculate simple dominance quotient
        dq = player_stats.get('dominance_quotient', 
                             self.calculator.calculate_dominance_quotient(player_stats, all_players))
        
        # Calculate ranking
        all_dqs = [p.get('dominance_quotient', 50.0) for p in all_players]
        dq_ranking = self.calculator.calculate_percentile(dq, all_dqs)
        dq_indicator = self.get_performance_indicator(dq_ranking)
        
        # Calculate overall rank for player name prefix
        all_dqs_sorted = sorted(all_dqs, reverse=True)
        overall_rank = all_dqs_sorted.index(dq) + 1 if dq in all_dqs_sorted else len(all_dqs) + 1

        # Helper to get rank emoji prefix for player name
        def _get_player_name_prefix(rank: int) -> str:
            if rank == 1:
                return "🥇 "
            elif rank == 2:
                return "🥈 "
            elif rank == 3:
                return "🥉 "
            else:
                digit_map = {'0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
                             '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'}
                return "".join(digit_map.get(digit, '') for digit in str(rank)) + " "

        player_name_prefix = _get_player_name_prefix(overall_rank)
        
        # Main embed
        embed = discord.Embed(
            title=f"{player_name_prefix}{user.display_name}'s BLCSX Profile",
            color=0x7289DA
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # === DOMINANCE QUOTIENT (Most Important) ===
        embed.add_field(
            name="PERFORMANCE SCORE (Overall Skill)",
            value=f"**DQ: {dq:.1f}** ({dq_indicator['name']})\n"
                  f"Percentile: {dq_ranking:.1f}th",
            inline=False
        )
        
        # === CORE PERFORMANCE STATS ===
        embed.add_field(
            name="Core Performance",
            value=f"Games Played: {player_stats['games_played']}\n"
                  f"Win Rate: {win_rate:.1f}% ({player_stats['wins']}W-{player_stats['losses']}L)",
            inline=True
        )
        
        # === KEY STATS ===
        key_stats = []
        
        # Helper to get rank display with emojis
        def _get_stat_rank_display(player_value, all_players_data, stat_key, higher_is_better=True):
            all_values = sorted([p.get(stat_key, 0) for p in all_players_data if p.get(stat_key) is not None], reverse=higher_is_better)
            if not all_values:
                return ""
            
            try:
                rank = all_values.index(player_value) + 1
                total = len(all_values)
                
                if rank <= 3: # Top 3
                    if rank == 1: return " 🥇"
                    if rank == 2: return " 🥈"
                    if rank == 3: return " 🥉"
                elif rank > total - 3: # Bottom 3
                    return " 🔻"
                return ""
            except ValueError: 
                return ""

        key_stats.append(f"Average Score: {player_stats.get('avg_score', 0):.0f}{_get_stat_rank_display(player_stats.get('avg_score', 0), all_players, 'avg_score', higher_is_better=True)}")
        key_stats.append(f"Goals/Game: {player_stats.get('goals_per_game', 0):.2f}{_get_stat_rank_display(player_stats.get('goals_per_game', 0), all_players, 'goals_per_game', higher_is_better=True)}")
        key_stats.append(f"Assists/Game: {player_stats.get('assists_per_game', 0):.2f}{_get_stat_rank_display(player_stats.get('assists_per_game', 0), all_players, 'assists_per_game', higher_is_better=True)}")
        key_stats.append(f"Saves/Game: {player_stats.get('saves_per_game', 0):.2f}{_get_stat_rank_display(player_stats.get('saves_per_game', 0), all_players, 'saves_per_game', higher_is_better=True)}")
        key_stats.append(f"Shot %: {player_stats.get('shot_percentage', 0):.1f}%{_get_stat_rank_display(player_stats.get('shot_percentage', 0), all_players, 'shot_percentage', higher_is_better=True)}")
        key_stats.append(f"Avg Speed: {player_stats.get('avg_speed', 0):.0f}{_get_stat_rank_display(player_stats.get('avg_speed', 0), all_players, 'avg_speed', higher_is_better=True)}")
        
        embed.add_field(
            name="Key Statistics",
            value="\n".join(key_stats),
            inline=True
        )
        
        
        
        embed.set_footer(text=f"BLCSX Season 4 | Last updated: {player_stats.get('last_updated', 'Unknown')}")
        
        return embed

    async def process_group_data(self, group_id: str, season_id: str = "BLCS4"):
        """Process all data from a ballchasing group"""
        if not self.ballchasing_token:
            raise Exception("BALLCHASING_API_KEY not configured")
        
        logger.info(f"Processing group data for {group_id}")
        
        async with BallchasingAPI(self.ballchasing_token) as api:
            group_data = await api.get_group_data(group_id)
            if not group_data:
                raise Exception("Failed to get group data")
            
            players_data = group_data.get('players', [])
            logger.info(f"Found {len(players_data)} players")
            
            # Process individual player statistics
            processed_players = []
            for player in players_data:
                player_stats = self.extract_player_stats(player, season_id)
                if player_stats:
                    processed_players.append(player_stats)
            
            # Calculate dominance quotients for all players
            for player_stats in processed_players:
                player_stats['dominance_quotient'] = self.calculator.calculate_dominance_quotient(player_stats, processed_players)

            # Now that all DQs are calculated, determine percentile ranks and update the database
            all_dqs = [p['dominance_quotient'] for p in processed_players]
            for player_stats in processed_players:
                percentile_rank = self.calculator.calculate_percentile(player_stats['dominance_quotient'], all_dqs)
                player_stats['percentile_rank'] = percentile_rank
                
                # Update database with the fully processed stats
                self.db.update_player_statistics(player_stats)
            
            logger.info(f"Processed {len(processed_players)} players successfully")
    
    def extract_player_stats(self, player_data: Dict, season_id: str) -> Dict:
        """Extract and calculate player statistics from API data"""
        try:
            # Ballchasing API can return platform as a string or a dict
            platform_type = player_data.get('platform')
            platform_id = player_data.get('id')

            if isinstance(platform_type, dict):
                # Newer API response format
                player_id = f"{platform_type.get('type')}:{platform_type.get('id')}"
            elif isinstance(platform_type, str) and isinstance(platform_id, str):
                # Older API response format or simplified
                player_id = f"{platform_type.lower()}:{platform_id}"
            else:
                # Fallback for unexpected formats
                logger.error(f"Could not determine player_id from platform_info: {player_data}")
                return None
            
            logger.info(f"Extracted player_id from Ballchasing API: {player_id}")
            cumulative = player_data.get('cumulative', {})
            game_average = player_data.get('game_average', {})
            
            # Core stats
            core_avg = game_average.get('core', {})
            movement_stats = game_average.get('movement', {})
            demo_stats = game_average.get('demo', {})
            
            extracted_stats = {
                'player_id': player_id,
                'season_id': season_id,
                'games_played': cumulative.get('games', 0),
                'wins': cumulative.get('wins', 0),
                'losses': cumulative.get('games', 0) - cumulative.get('wins', 0),
                'avg_score': core_avg.get('score', 0),
                'goals_per_game': core_avg.get('goals', 0),
                'assists_per_game': core_avg.get('assists', 0),
                'saves_per_game': core_avg.get('saves', 0),
                'shots_per_game': core_avg.get('shots', 0),
                'shot_percentage': core_avg.get('shooting_percentage', 0),
                'demos_inflicted_per_game': demo_stats.get('inflicted', 0),
                'demos_taken_per_game': demo_stats.get('taken', 0),
                'avg_speed': movement_stats.get('avg_speed', 0),
                'dominance_quotient': 0,
                'percentile_rank': 0
            }
            logger.info(f"Returning extracted stats for {player_id}: {extracted_stats}")
            return extracted_stats
        except Exception as e:
            logger.error(f"Error extracting player stats: {e}")
            return None

    # === SLASH COMMANDS ===

    @discord.slash_command(name="blcs_profile", description="Show comprehensive BLCSX player profile with rankings")
    async def profile_command(self, ctx, player: discord.Member = None):
        """Modern profile command with detailed rankings"""
        target_user = player or ctx.author
        
        await ctx.response.defer()
        
        try:
            # Get player mapping
            mapping = self.db.get_player_mapping(target_user.id)
            if not mapping:
                embed = discord.Embed(
                    title="Player Not Found",
                    description=f"No ballchasing.com mapping found for {target_user.display_name}.\nUse `/blcs_link` to connect your account.",
                    color=discord.Color.red()
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Get player statistics
            player_stats = self.db.get_player_statistics(mapping['ballchasing_player_id'])
            if not player_stats:
                embed = discord.Embed(
                    title="No Statistics",
                    description=f"No statistics found for {target_user.display_name}.\nData may still be processing.",
                    color=discord.Color.orange()
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Get all players for comparison
            all_players = self.db.get_all_player_statistics()
            
            # Generate modern profile embed
            embed = self.create_profile_embed(target_user, player_stats, all_players)
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in profile command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while generating the profile.",
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="blcs_link", description="Link your Discord account to your ballchasing.com player ID")
    async def link_command(self, ctx, player_id: str, platform: str):
        """Link Discord account to ballchasing player ID"""
        
        # Validate platform
        valid_platforms = ['steam', 'epic', 'ps4', 'xbox', 'switch']
        if platform.lower() not in valid_platforms:
            embed = discord.Embed(
                title="Invalid Platform",
                description=f"Platform must be one of: {', '.join(valid_platforms)}",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)
            return
        
        # Format player ID correctly
        if ':' not in player_id:
            formatted_player_id = f"{platform.lower()}:{player_id}"
        else:
            formatted_player_id = player_id
        
        try:
            # Add mapping to database
            self.db.add_player_mapping(
                ctx.author.id,
                ctx.author.display_name,
                formatted_player_id,
                platform.lower()
            )
            
            embed = discord.Embed(
                title="Account Linked",
                description=f"Successfully linked {ctx.author.display_name} to {formatted_player_id}",
                color=discord.Color.green()
            )
            await ctx.response.send_message(embed=embed)
            logger.info(f"User {ctx.author.display_name} ({ctx.author.id}) linked to Ballchasing ID: {formatted_player_id}")
            
        except Exception as e:
            logger.error(f"Error linking account: {e}")
            embed = discord.Embed(
                title="Error",
                description="Failed to link account. Please try again.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

    @discord.slash_command(name="compare", description="Compare two players' BLCSX profiles side-by-side")
    async def compare_command(self, ctx, player1: discord.Member, player2: discord.Member):
        """Compares two players' profiles."""
        await ctx.response.defer()

        try:
            # Get stats for Player 1
            mapping1 = self.db.get_player_mapping(player1.id)
            if not mapping1 or not mapping1.get('ballchasing_player_id'):
                await ctx.followup.send(f"❌ {player1.display_name} has not linked their ballchasing.com account.", ephemeral=True)
                return
            stats1 = self.db.get_player_statistics(mapping1['ballchasing_player_id'])
            if not stats1:
                await ctx.followup.send(f"📊 No statistics found for {player1.display_name}.", ephemeral=True)
                return

            # Get stats for Player 2
            mapping2 = self.db.get_player_mapping(player2.id)
            if not mapping2 or not mapping2.get('ballchasing_player_id'):
                await ctx.followup.send(f"❌ {player2.display_name} has not linked their ballchasing.com account.", ephemeral=True)
                return
            stats2 = self.db.get_player_statistics(mapping2['ballchasing_player_id'])
            if not stats2:
                await ctx.followup.send(f"📊 No statistics found for {player2.display_name}.", ephemeral=True)
                return

            all_players_data = self.db.get_all_player_statistics()

            embed = discord.Embed(
                title=f"📊 {player1.display_name} vs {player2.display_name}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=player1.display_avatar.url)
            embed.set_image(url=player2.display_avatar.url) # This will show player2's avatar below

            # Helper to format stat lines
            def format_stat_line(stat_name, stat1_value, stat2_value, is_percentage=False, decimal_places=2):
                if is_percentage:
                    s1 = f"{stat1_value:.1f}%"
                    s2 = f"{stat2_value:.1f}%"
                elif decimal_places == 0:
                    s1 = f"{stat1_value:.0f}"
                    s2 = f"{stat2_value:.0f}"
                else:
                    s1 = f"{stat1_value:.{decimal_places}f}"
                    s2 = f"{stat2_value:.{decimal_places}f}"

                if stat1_value > stat2_value:
                    return f"**{stat_name}:** {s1} > {s2}"
                elif stat2_value > stat1_value:
                    return f"**{stat_name}:** {s1} < {s2}"
                else:
                    return f"**{stat_name}:** {s1} = {s2}"

            # Dominance Quotient
            dq1 = stats1.get('dominance_quotient', 0)
            dq2 = stats2.get('dominance_quotient', 0)
            embed.add_field(
                name="Overall Dominance Quotient",
                value=format_stat_line("DQ", dq1, dq2, decimal_places=1),
                inline=False
            )

            # Core Stats
            embed.add_field(
                name="Core Stats",
                value=(
                    f"Games Played: {stats1.get('games_played', 0)} vs {stats2.get('games_played', 0)}\n"
                    f"Win Rate: {stats1.get('wins', 0) / max(stats1.get('games_played', 1), 1) * 100:.1f}% vs {stats2.get('wins', 0) / max(stats2.get('games_played', 1), 1) * 100:.1f}%\n"
                    f"{format_stat_line("Avg Score", stats1.get('avg_score', 0), stats2.get('avg_score', 0), decimal_places=0)}"
                ),
                inline=True
            )

            # Key Stats
            embed.add_field(
                name="Key Stats",
                value=(
                    f"{format_stat_line("Goals/Game", stats1.get('goals_per_game', 0), stats2.get('goals_per_game', 0))}\n"
                    f"{format_stat_line("Assists/Game", stats1.get('assists_per_game', 0), stats2.get('assists_per_game', 0))}\n"
                    f"{format_stat_line("Saves/Game", stats1.get('saves_per_game', 0), stats2.get('saves_per_game', 0))}\n"
                    f"{format_stat_line("Shot %", stats1.get('shot_percentage', 0), stats2.get('shot_percentage', 0), is_percentage=True)}\n"
                    f"{format_stat_line("Avg Speed", stats1.get('avg_speed', 0), stats2.get('avg_speed', 0), decimal_places=0)}"
                ),
                inline=True
            )

            embed.set_footer(text="Comparison based on BLCSX Season 4 data")
            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in compare command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while comparing profiles. Please check the logs.",
                color=discord.Color.dark_red()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)

    def _generate_roast(self, player_stats: Dict, all_players_data: List[Dict]) -> str:
        """Generates a light-hearted roast based on player statistics."""
        dq = player_stats.get('dominance_quotient', 0)
        avg_score = player_stats.get('avg_score', 0)
        goals = player_stats.get('goals_per_game', 0)
        assists = player_stats.get('assists_per_game', 0)
        saves = player_stats.get('saves_per_game', 0)
        shots = player_stats.get('shots_per_game', 0)
        shot_pct = player_stats.get('shot_percentage', 0)
        demos_inflicted = player_stats.get('demos_inflicted_per_game', 0)
        demos_taken = player_stats.get('demos_taken_per_game', 0)
        games_played = player_stats.get('games_played', 0)
        wins = player_stats.get('wins', 0)
        losses = player_stats.get('losses', 0)

        roasts = []

        # General performance
        if dq < 30:
            roasts.append("Are you sure you're playing Rocket League? Your DQ suggests you might be playing 'Carball Simulator: AFK Edition'.")
        elif dq < 50:
            roasts.append("Your Dominance Quotient is so average, it's practically a participation trophy.")
        elif dq > 80:
            roasts.append("Wow, your DQ is so high, do you even let your teammates touch the ball?")

        # Score
        if avg_score < 200:
            roasts.append("Your average score is lower than my grandma's ping. Are you sure you're not just spectating?")
        elif avg_score > 600:
            roasts.append("Your score is so high, I'm starting to think you're playing against bots... or toddlers.")

        # Goals
        if goals < 0.5:
            roasts.append("Do you even know where the opponent's net is? It's the big thing on the other side of the field, just in case you were wondering.")
        elif goals > 1.5:
            roasts.append("You score so much, I bet your teammates are starting to feel a bit redundant.")

        # Saves
        if saves < 0.5:
            roasts.append("Your net is more open than a 24/7 diner. Maybe try blocking a few shots instead of admiring the scenery?")
        elif saves > 2.5:
            roasts.append("You're a save machine! Are you secretly a brick wall with a controller?")

        # Assists
        if assists < 0.3:
            roasts.append("Do you pass? Or do you just believe in the 'every man for himself' philosophy?")
        elif assists > 1.0:
            roasts.append("You're dishing out assists like candy on Halloween. Are you trying to make friends or win games?")

        # Shot Percentage
        if shot_pct < 10:
            roasts.append("Your shot percentage is so low, you're practically shooting blanks. Maybe try aiming for the net, not the moon?")
        elif shot_pct > 40:
            roasts.append("Your shot percentage is insane! Are you using a cheat code or just a really big magnet?")

        # Demos
        if demos_inflicted > 1.5:
            roasts.append("You're a demolition derby enthusiast, aren't you? This is Rocket League, not Mad Max!")
        elif demos_taken > 1.5:
            roasts.append("You're getting demo'd more often than a cheap tent in a hurricane. Maybe try dodging once in a while?")

        # Win/Loss
        if games_played > 5 and losses > wins * 2:
            roasts.append("Your win-loss record is looking a bit like a downhill ski slope. Time to hit the brakes?")
        elif games_played > 5 and wins > losses * 2:
            roasts.append("Your win streak is so impressive, I'm starting to think you've bribed the Rocket League gods.")

        if not roasts:
            roasts.append("You're so perfectly average, I can't even come up with a good roast. Congrats, I guess?")

        return random.choice(roasts)

    def _generate_roast(self, player_stats: Dict, all_players_data: List[Dict]) -> str:
        """Generates a light-hearted roast based on player statistics."""
        dq = player_stats.get('dominance_quotient', 0)
        avg_score = player_stats.get('avg_score', 0)
        goals = player_stats.get('goals_per_game', 0)
        assists = player_stats.get('assists_per_game', 0)
        saves = player_stats.get('saves_per_game', 0)
        shots = player_stats.get('shots_per_game', 0)
        shot_pct = player_stats.get('shot_percentage', 0)
        demos_inflicted = player_stats.get('demos_inflicted_per_game', 0)
        demos_taken = player_stats.get('demos_taken_per_game', 0)
        games_played = player_stats.get('games_played', 0)
        wins = player_stats.get('wins', 0)
        losses = player_stats.get('losses', 0)

        roasts = []

        # General performance
        if dq < 30:
            roasts.append("Are you sure you're playing Rocket League? Your DQ suggests you might be playing 'Carball Simulator: AFK Edition'.")
        elif dq < 50:
            roasts.append("Your Dominance Quotient is so average, it's practically a participation trophy.")
        elif dq > 80:
            roasts.append("Wow, your DQ is so high, do you even let your teammates touch the ball?")

        # Score
        if avg_score < 200:
            roasts.append("Your average score is lower than my grandma's ping. Are you sure you're not just spectating?")
        elif avg_score > 600:
            roasts.append("Your score is so high, I'm starting to think you're playing against bots... or toddlers.")

        # Goals
        if goals < 0.5:
            roasts.append("Do you even know where the opponent's net is? It's the big thing on the other side of the field, just in case you were wondering.")
        elif goals > 1.5:
            roasts.append("You score so much, I bet your teammates are starting to feel a bit redundant.")

        # Saves
        if saves < 0.5:
            roasts.append("Your net is more open than a 24/7 diner. Maybe try blocking a few shots instead of admiring the scenery?")
        elif saves > 2.5:
            roasts.append("You're a save machine! Are you secretly a brick wall with a controller?")

        # Assists
        if assists < 0.3:
            roasts.append("Do you pass? Or do you just believe in the 'every man for himself' philosophy?")
        elif assists > 1.0:
            roasts.append("You're dishing out assists like candy on Halloween. Are you trying to make friends or win games?")

        # Shot Percentage
        if shot_pct < 10:
            roasts.append("Your shot percentage is so low, you're practically shooting blanks. Maybe try aiming for the net, not the moon?")
        elif shot_pct > 40:
            roasts.append("Your shot percentage is insane! Are you using a cheat code or just a really big magnet?")

        # Demos
        if demos_inflicted > 1.5:
            roasts.append("You're a demolition derby enthusiast, aren't you? This is Rocket League, not Mad Max!")
        elif demos_taken > 1.5:
            roasts.append("You're getting demo'd more often than a cheap tent in a hurricane. Maybe try dodging once in a while?")

        # Win/Loss
        if games_played > 5 and losses > wins * 2:
            roasts.append("Your win-loss record is looking a bit like a downhill ski slope. Time to hit the brakes?")
        elif games_played > 5 and wins > losses * 2:
            roasts.append("Your win streak is so impressive, I'm starting to think you've bribed the Rocket League gods.")

        if not roasts:
            roasts.append("You're so perfectly average, I can't even come up with a good roast. Congrats, I guess?")

        return random.choice(roasts)

    def _generate_player_summary(self, player_stats: Dict, all_players_data: List[Dict]) -> str:
        """Generates a narrative summary of a player's performance based on their stats and league comparison."""
        summary_phrases = []

        # Get overall DQ and its percentile
        dq = player_stats.get('dominance_quotient', 0)
        all_dqs = [p.get('dominance_quotient', 0) for p in all_players_data]
        dq_percentile = self.calculator.calculate_percentile(dq, all_dqs)

        # Overall performance summary
        if dq_percentile >= 90:
            summary_phrases.append(f"<@{player_stats['discord_id']}> had an absolutely dominant performance, showcasing elite skill across the board.")
        elif dq_percentile >= 70:
            summary_phrases.append(f"<@{player_stats['discord_id']}> delivered a strong performance, consistently ranking among the top players.")
        elif dq_percentile >= 40:
            summary_phrases.append(f"<@{player_stats['discord_id']}> put in a solid, all-around effort, holding their own in the league.")
        else:
            summary_phrases.append(f"<@{player_stats['discord_id']}> faced some challenges this season, with their performance indicating room for growth.")

        # Win/Loss record
        games_played = player_stats.get('games_played', 0)
        wins = player_stats.get('wins', 0)
        losses = player_stats.get('losses', 0)
        if games_played > 0:
            win_rate = (wins / games_played) * 100
            if win_rate >= 70:
                summary_phrases.append(f"Their team secured an impressive {win_rate:.1f}% win rate, demonstrating strong teamwork and execution.")
            elif win_rate >= 50:
                summary_phrases.append(f"With a {win_rate:.1f}% win rate, they contributed to a balanced team effort.")
            else:
                summary_phrases.append(f"Despite their efforts, their team struggled with a {win_rate:.1f}% win rate.")

        # Key stat highlights (compare to league average/percentiles)
        stat_highlights = []
        stats_to_check = {
            'goals_per_game': {'name': 'goals', 'threshold_elite': 1.2, 'threshold_good': 0.8},
            'assists_per_game': {'name': 'assists', 'threshold_elite': 1.0, 'threshold_good': 0.7},
            'saves_per_game': {'name': 'saves', 'threshold_elite': 2.0, 'threshold_good': 1.5},
            'avg_score': {'name': 'average score', 'threshold_elite': 450, 'threshold_good': 380},
        }

        for stat_key, info in stats_to_check.items():
            player_value = player_stats.get(stat_key, 0)
            all_values = [p.get(stat_key, 0) for p in all_players_data if p.get(stat_key) is not None]
            if not all_values: continue
            
            stat_percentile = self.calculator.calculate_percentile(player_value, all_values)

            if stat_percentile >= 90:
                stat_highlights.append(f"Their {info['name']} per game ({player_value:.2f}) was exceptional, ranking among the league's best.")
            elif stat_percentile >= 75:
                stat_highlights.append(f"They showed strong performance in {info['name']} per game ({player_value:.2f}).")
            elif stat_percentile <= 10:
                stat_highlights.append(f"However, their {info['name']} per game ({player_value:.2f}) was notably low, indicating an area for improvement.")

        if stat_highlights:
            summary_phrases.append("\n" + " ".join(stat_highlights))

        # Add a concluding remark
        summary_phrases.append("\nOverall, a season of valuable experience and growth for the player.")

        return " ".join(summary_phrases)

    @discord.slash_command(name="blcs_summary", description="Get a narrative summary of a player's performance")
    async def blcs_summary_command(self, ctx, player: discord.Member = None):
        """Generates a narrative summary for a player."""
        target_user = player or ctx.author
        await ctx.response.defer()

        try:
            mapping = self.db.get_player_mapping(target_user.id)
            if not mapping or not mapping.get('ballchasing_player_id'):
                await ctx.followup.send(f"❌ {target_user.display_name} has not linked their ballchasing.com account. Cannot generate summary.", ephemeral=True)
                return
            stats = self.db.get_player_statistics(mapping['ballchasing_player_id'])
            if not stats:
                await ctx.followup.send(f"📊 No statistics found for {target_user.display_name}. Cannot generate summary.", ephemeral=True)
                return
            
            all_players = self.db.get_all_player_statistics()
            summary_message = self._generate_player_summary(stats, all_players)

            embed = discord.Embed(
                title=f"📝 Player Summary: {target_user.display_name}",
                description=summary_message,
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in blcs_summary command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while generating the player summary.",
                color=discord.Color.dark_red()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)

    @discord.slash_command(name="admin_blcs_link", description="[Admin] Link a player to their ballchasing.com ID")
    @commands.has_permissions(administrator=True)
    async def admin_link_command(self, ctx, user: discord.Member, player_id: str, platform: str):
        """Admin command to link a user to their ballchasing ID."""
        valid_platforms = ['steam', 'epic', 'ps4', 'xbox', 'switch']
        if platform.lower() not in valid_platforms:
            embed = discord.Embed(
                title="Invalid Platform",
                description=f"Platform must be one of: {', '.join(valid_platforms)}",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return

        if ':' not in player_id:
            formatted_player_id = f"{platform.lower()}:{player_id}"
        else:
            formatted_player_id = player_id

        try:
            self.db.add_player_mapping(
                user.id,
                user.display_name,
                formatted_player_id,
                platform.lower()
            )

            embed = discord.Embed(
                title="✅ Player Linked by Admin",
                description=f"Successfully linked {user.display_name} to {formatted_player_id}",
                color=discord.Color.green()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"Admin {ctx.author.display_name} ({ctx.author.id}) linked user {user.display_name} ({user.id}) to Ballchasing ID: {formatted_player_id}")

        except Exception as e:
            logger.error(f"Error in admin_link_command: {e}")
            embed = discord.Embed(
                title="Error",
                description="Failed to link player. Please check logs.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)

    @discord.slash_command(name="blcs_update", description="Update player statistics from ballchasing.com (Admin only)")
    async def update_data_command(self, ctx, group_id: str):
        """Update player data from ballchasing.com"""
        
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="Permission Denied",
                description="Only administrators can update data.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)
            return
        
        await ctx.response.defer()
        
        try:
            await self.process_group_data(group_id)
            
            embed = discord.Embed(
                title="Data Updated",
                description=f"Successfully processed data from group {group_id}",
                color=discord.Color.green()
            )
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")
            embed = discord.Embed(
                title="Error",
                description=f"Failed to update data: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="blcs_clear_stats", description="[Admin] Clears all player statistics from the database.")
    @commands.has_permissions(administrator=True)
    async def clear_stats_command(self, ctx):
        """Clears all player statistics from the database."""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="Permission Denied",
                description="Only administrators can clear player statistics.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return

        await ctx.response.defer(ephemeral=True)

        try:
            with self.db.Session() as session:
                session.query(PlayerStatistics).delete()
                session.commit()
            embed = discord.Embed(
                title="✅ Player Statistics Cleared",
                description="All player statistics have been successfully removed from the database.",
                color=discord.Color.green()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Admin {ctx.author.display_name} ({ctx.author.id}) cleared all player statistics.")
        except Exception as e:
            logger.error(f"Error clearing player statistics: {e}")
            embed = discord.Embed(
                title="❌ Error Clearing Stats",
                description=f"An error occurred while clearing player statistics: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)

    @discord.slash_command(name="all_player_stats", description="Show all the stats for players")
    @commands.has_permissions(administrator=True)
    async def all_player_stats(self, ctx):    
        await ctx.response.defer()

        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as patches
            from io import BytesIO
            from pathlib import Path
            import numpy as np

            try:
                cfg = OmegaConf.load("conf/config.yaml")
            except Exception as e:
                logger.error("Can not find config yaml file for channel id")
                logger.error(f"Error: {e}")
            
            all_players = self.db.get_all_player_statistics()
            df = pd.DataFrame(all_players)
            logger.info(df.columns)
            
            df = df[[
                "discord_username",
                "avg_score",
                "goals_per_game",
                "saves_per_game",
                "shots_per_game",
                "shot_percentage",
                "dominance_quotient",
                "demos_inflicted_per_game",
                "demos_taken_per_game",
            ]]
            
            try:
                df["discord_username"] = df['discord_username'].str.split("|").str[0]
            except Exception as e:
                logger.error(f"Error splitting and getting first index: {e}")

            df = df.sort_values(by="dominance_quotient", ascending=False)  # Fixed typo: asending -> ascending
            
            # Store original values before rounding for min/max calculations
            numeric_cols = df.select_dtypes(include="number").columns
            original_df = df[numeric_cols].copy()
            
            try:
                for col in numeric_cols:
                    df[col] = df[col].round(2)
            except Exception as e:
                logger.error(f"Error rounding values: {e}")

            # Rename columns AFTER calculating min/max
            column_mapping = {
                "discord_username": "Player",
                "avg_score": "Avg Score",
                "goals_per_game": "Avg Goals",
                "saves_per_game": "Avg Saves", 
                "shots_per_game": "Avg Shots",
                "shot_percentage": "Shot %",
                "dominance_quotient": "DQ",
                "demos_inflicted_per_game": "Demos Inf.",
                "demos_taken_per_game": "Demos Taken"
            }
            
            df = df.rename(columns=column_mapping)

            channel_id = cfg.channel.player_stats_id
            stats_channel = self.bot.get_channel(channel_id)
            
            fig, ax = plt.subplots(figsize=(18, max(8, df.shape[0] * 0.4)))
            ax.axis('tight')
            ax.axis('off')
            
            table = ax.table(cellText=df.values,
                            colLabels=df.columns,
                            cellLoc='center',
                            loc='center',
                            bbox=[0,0,1,1])
            
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 2)

            # Define colors - Dark bluish-black theme
            dark_blue_light = '#2C3E50'    # Dark blue-gray (lighter alternate)
            dark_blue_dark = '#1B2631'     # Very dark blue-black (darker alternate)
            header_blue = '#34495E'        # Header dark blue
            green_highlight = '#27AE60'    # Bright green for best
            red_highlight = '#E74C3C'      # Bright red for worst
            gold_highlight = '#F39C12'     # Gold for first place

            # Style header row
            for j in range(len(df.columns)):
                table[(0, j)].set_facecolor(header_blue)
                table[(0, j)].set_text_props(weight='bold', color='white')

            # Find min/max for each numeric column (using original values)
            stat_columns = ['Avg Score', 'Avg Goals', 'Avg Saves', 
                        'Avg Shots', 'Shot %', 'DQ', 'Demos Inf.', 'Demos Taken']
            
            # Columns where higher is better
            higher_is_better = ['Avg Score', 'Avg Goals', 'Avg Saves', 'Avg Shots', 'Shot %', 'DQ', 'Demos Inf.']
            # Columns where lower is better  
            lower_is_better = ['Demos Taken']
            # Neutral columns (just alternate colors)
            neutral_cols = []

            # Color each cell
            for i in range(1, len(df) + 1):  # Skip header row
                # Check if this is the first place (highest DQ)
                is_first_place = (i == 1)  # Since we sorted by DQ descending, first row is #1
                
                # Base alternating color
                base_color = dark_blue_light if i % 2 == 1 else dark_blue_dark
                
                for j, col_name in enumerate(df.columns):
                    cell_color = base_color
                    text_color = 'white'  # Default white text on dark background
                    
                    # Special gold highlighting for first place row
                    if is_first_place:
                        cell_color = gold_highlight
                        text_color = 'black'  # Black text on gold background for better readability
                    elif col_name in stat_columns and col_name not in neutral_cols:
                        # Get the column data for comparison
                        col_data = df[col_name].astype(float)
                        current_value = float(df.iloc[i-1, j])
                        
                        if col_name in higher_is_better:
                            if current_value == col_data.max():
                                cell_color = green_highlight
                                text_color = 'white'
                            elif current_value == col_data.min():
                                cell_color = red_highlight
                                text_color = 'white'
                        elif col_name in lower_is_better:
                            if current_value == col_data.min():
                                cell_color = green_highlight
                                text_color = 'white'
                            elif current_value == col_data.max():
                                cell_color = red_highlight
                                text_color = 'white'
                    
                    table[(i, j)].set_facecolor(cell_color)
                    
                    # Set text color and make bold for highlighted cells
                    if cell_color in [green_highlight, red_highlight, gold_highlight]:
                        table[(i, j)].set_text_props(weight='bold', color=text_color)
                    else:
                        table[(i, j)].set_text_props(color=text_color)

            plt.title("BLCSX Player Statistics", fontsize=18, fontweight='bold', pad=20, color='white')
            
            # Set the figure background to dark
            fig.patch.set_facecolor('#1B2631')
            ax.set_facecolor('#1B2631')

            img_buffer = BytesIO()
            plt.savefig(img_buffer, format="png", dpi=300, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close()

            file = discord.File(img_buffer, filename='blcsx_player_stats.png')

            embed = discord.Embed(
                title="📊 BLCSX Player Statistics",
                description=f"Complete statistics for all {len(df)} players\n🥇 Gold = 1st Place | 🟢 Green = Best in category | 🔴 Red = Worst in category",
                color=0x34495E  # Dark blue color
            )

            await stats_channel.send(embed=embed, file=file)
            await ctx.followup.send("✅ Player stats table sent with color coding!")
            
        except Exception as e:
            logger.error(f"Error in all_player_stats command: {e}")
            await ctx.followup.send(f"Error: {str(e)}")

    @discord.slash_command(name="blcs_leaderboard", description="Show the performance score leaderboard")
    async def leaderboard_command(self, ctx, limit: int = 10):
        """Enhanced leaderboard with performance indicators"""
        
        try:
            all_players = self.db.get_all_player_statistics()
            all_mappings = self.db.get_all_player_mappings()
            
            # Create a lookup table for player names
            # This is no longer needed due to the JOIN in the query
            
            if not all_players:
                embed = discord.Embed(
                    title="No Data",
                    description="No player statistics available yet. Use `/blcs_update` to fetch them.",
                    color=discord.Color.orange()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            # The list is already sorted by the database query
            limited_players = all_players[:min(limit, len(all_players))]
            
            # Create leaderboard embed
            embed = discord.Embed(
                title="🏆 BLCSX Performance Leaderboard",
                description="Rankings based on overall player performance analysis",
                color=discord.Color.gold()
            )
            
            leaderboard_text = ""
            for i, player in enumerate(limited_players, 1):
                # Use the joined discord_username, with a fallback to the player_id
                player_name = player.get('discord_username') or player['player_id']
                dq = player.get('dominance_quotient', 0)
                win_rate = (player['wins'] / max(player['games_played'], 1)) * 100
                
                # Get performance indicator
                indicator = self.get_performance_indicator(dq)
                
                # Medal for top 3
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"{i}."
                
                leaderboard_text += f"{medal} **{player_name}** ({indicator['name']})\n"
                leaderboard_text += f"    DQ: **{dq:.1f}** | Avg Score: **{player.get('avg_score', 0):.0f}** | {win_rate:.1f}% WR\n\n"
            
            embed.add_field(
                name="📊 Rankings",
                value=leaderboard_text,
                inline=False
            )
            
            embed.set_footer(text=f"Showing top {len(limited_players)} of {len(all_players)} players")
            
            await ctx.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while generating the leaderboard.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

    @discord.slash_command(name="roast", description="Get roasted based on your BLCSX stats!")
    async def roast_command(self, ctx, player: discord.Member = None):
        """Roasts a player based on their statistics."""
        target_user = player or ctx.author
        await ctx.response.defer()

        try:
            mapping = self.db.get_player_mapping(target_user.id)
            if not mapping or not mapping.get('ballchasing_player_id'):
                await ctx.followup.send(f"❌ {target_user.display_name} has not linked their ballchasing.com account. Can't roast what I can't see!", ephemeral=True)
                return
            stats = self.db.get_player_statistics(mapping['ballchasing_player_id'])
            if not stats:
                await ctx.followup.send(f"📊 No statistics found for {target_user.display_name}. Can't roast what isn't there!", ephemeral=True)
                return
            
            all_players = self.db.get_all_player_statistics()
            roast_message = self._generate_roast(stats, all_players)

            embed = discord.Embed(
                title=f"🔥 Roast Session: {target_user.display_name}",
                description=roast_message,
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            await ctx.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in roast command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred during the roast. Maybe you're unroastable?",
                color=discord.Color.dark_red()
            )
            await ctx.followup.send(embed=embed, ephemeral=True)

    def _create_stat_leaderboard_command(self, stat_key: str, display_name: str, higher_is_better: bool = True):
        async def stat_leaderboard_command(self, ctx, limit: int = 10):
            """Generates a leaderboard for a specific statistic."""
            try:
                all_players = self.db.get_all_player_statistics()
                
                if not all_players:
                    embed = discord.Embed(
                        title="No Data",
                        description="No player statistics available yet. Use `/blcs_update` to fetch them.",
                        color=discord.Color.orange()
                    )
                    await ctx.response.send_message(embed=embed)
                    return
                
                # Filter out players without the specific stat or with None values
                filtered_players = [p for p in all_players if p.get(stat_key) is not None]
                
                # Sort players by the specific stat
                sorted_players = sorted(filtered_players, key=lambda x: x.get(stat_key, 0), reverse=higher_is_better)
                
                limited_players = sorted_players[:min(limit, len(sorted_players))]
                
                embed = discord.Embed(
                    title=f"📊 BLCSX {display_name} Leaderboard",
                    description=f"Top players by {display_name}",
                    color=discord.Color.blue()
                )
                
                leaderboard_text = ""
                for i, player in enumerate(limited_players, 1):
                    player_name = player.get('discord_username') or player['player_id']
                    stat_value = player.get(stat_key, 0)
                    
                    if stat_key == 'shot_percentage':
                        stat_display = f"{stat_value:.1f}%"
                    elif stat_key in ['goals_per_game', 'assists_per_game', 'saves_per_game']:
                        stat_display = f"{stat_value:.2f}"
                    else:
                        stat_display = f"{stat_value:.0f}"
                    
                    # Medal for top 3
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    else:
                        medal = f"{i}."
                    
                    leaderboard_text += f"{medal} **{player_name}**: **{stat_display}**\n"
                
                embed.add_field(
                    name="Rankings",
                    value=leaderboard_text,
                    inline=False
                )
                
                embed.set_footer(text=f"Showing top {len(limited_players)} of {len(filtered_players)} players by {display_name}")
                
                await ctx.response.send_message(embed=embed)
                
            except Exception as e:
                logger.error(f"Error in {stat_key} leaderboard command: {e}")
                embed = discord.Embed(
                    title="Error",
                    description="An error occurred while generating the leaderboard.",
                    color=discord.Color.red()
                )
                await ctx.response.send_message(embed=embed)

        # Attach the command to the cog
        setattr(self, f"leaderboard_{stat_key.replace('_', '')}_command", commands.slash_command(
            name=f"leaderboard_{stat_key.replace('_per_game', '').replace('_percentage', '').replace('_', '')}",
            description=f"Show the leaderboard for {display_name}"
        )(stat_leaderboard_command.__get__(self, self.__class__)))

# Call the helper function for each desired stat
        self._create_stat_leaderboard_command(stat_key='goals_per_game', display_name='Goals/Game')
        self._create_stat_leaderboard_command(stat_key='assists_per_game', display_name='Assists/Game')
        self._create_stat_leaderboard_command(stat_key='saves_per_game', display_name='Saves/Game')
        self._create_stat_leaderboard_command(stat_key='shot_percentage', display_name='Shot Percentage')
        self._create_stat_leaderboard_command(stat_key='avg_speed', display_name='Average Speed')
        self._create_stat_leaderboard_command(stat_key='avg_score', display_name='Average Score')

def setup(bot):
    bot.add_cog(BLCSXStatsCog(bot))