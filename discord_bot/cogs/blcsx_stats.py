# cogs/blcsx_stats.py - Pure Py-cord Implementation
import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import numpy as np
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas/numpy not available - some features disabled")

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
                stmt = insert(PlayerStatistics).values(**player_stats)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['player_id'],
                    set_={k: stmt.excluded[k] for k in player_stats.keys() if k != 'player_id'}
                )
                session.execute(stmt)
                session.commit()
        except Exception as e:
            logger.error(f"Error updating player statistics: {e}")
    
    def get_player_statistics(self, player_id: str) -> Optional[Dict]:
        """Get player statistics"""
        if not self.use_db:
            return self.storage.get_player_statistics(player_id)
        
        try:
            with self.Session() as session:
                stats = session.query(PlayerStatistics).filter_by(player_id=player_id).first()
                if stats:
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
                return None
        except Exception as e:
            logger.error(f"Error getting player statistics: {e}")
            return None
    
    def get_all_player_statistics(self) -> List[Dict]:
        """Get all player statistics for ranking calculations"""
        if not self.use_db:
            return self.storage.get_all_player_statistics()
        
        try:
            with self.Session() as session:
                all_stats = session.query(PlayerStatistics).order_by(PlayerStatistics.dominance_quotient.desc()).all()
                return [{
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
                } for stats in all_stats]
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

class SimpleStatsCalculator:
    """Simple stats calculator when pandas is not available"""
    
    @staticmethod
    def calculate_simple_score(player_stats: Dict, all_players: List[Dict]) -> float:
        """Calculate a simple performance score without pandas"""
        if not all_players:
            return 50.0
        
        # Simple scoring based on win rate and basic stats
        win_rate = player_stats.get('wins', 0) / max(player_stats.get('games_played', 1), 1)
        goals = player_stats.get('goals_per_game', 0)
        assists = player_stats.get('assists_per_game', 0)
        saves = player_stats.get('saves_per_game', 0)
        
        # Simple weighted score
        score = (win_rate * 40) + (goals * 10) + (assists * 8) + (saves * 8)
        return min(100, max(0, score))
    
    @staticmethod
    def calculate_ranking(player_value: float, all_values: List[float]) -> Dict:
        """Calculate ranking without pandas"""
        if not all_values:
            return {'rank': 1, 'total': 1, 'percentile': 50.0}
        
        sorted_values = sorted(all_values, reverse=True)
        rank = 1
        for i, value in enumerate(sorted_values, 1):
            if player_value >= value:
                rank = i
                break
        
        percentile = (len([v for v in all_values if v < player_value]) / len(all_values)) * 100
        
        return {
            'rank': rank,
            'total': len(all_values),
            'percentile': max(0, min(100, percentile))
        }

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
        self.calculator = SimpleStatsCalculator()
        
        # Performance indicators
        self.performance_indicators = {
            'elite': {'emoji': '🏆', 'threshold': 90, 'color': 0x4CAF50, 'name': 'ELITE'},
            'excellent': {'emoji': '🥇', 'threshold': 80, 'color': 0x8BC34A, 'name': 'EXCELLENT'},
            'good': {'emoji': '✅', 'threshold': 65, 'color': 0xFFC107, 'name': 'GOOD'},
            'average': {'emoji': '➖', 'threshold': 35, 'color': 0xFF9800, 'name': 'AVERAGE'},
            'poor': {'emoji': '📉', 'threshold': 20, 'color': 0xF44336, 'name': 'POOR'},
            'terrible': {'emoji': '🔻', 'threshold': 0, 'color': 0xB71C1C, 'name': 'TERRIBLE'}
        }
        
        logger.info("BLCSX Stats Cog initialized")

    def get_performance_indicator(self, percentile: float) -> Dict:
        """Get performance indicator based on percentile"""
        for level, data in self.performance_indicators.items():
            if percentile >= data['threshold']:
                return data
        return self.performance_indicators['terrible']

    def create_profile_embed(self, user: discord.User, player_stats: Dict, all_players: List[Dict]) -> discord.Embed:
        """Create modern profile embed with rankings and indicators"""
        
        # Calculate win rate and basic stats
        win_rate = (player_stats['wins'] / max(player_stats['games_played'], 1)) * 100
        
        # Calculate simple dominance quotient
        dq = player_stats.get('dominance_quotient', 
                             self.calculator.calculate_simple_score(player_stats, all_players))
        
        # Calculate ranking
        all_dqs = [p.get('dominance_quotient', 50.0) for p in all_players]
        dq_ranking = self.calculator.calculate_ranking(dq, all_dqs)
        dq_indicator = self.get_performance_indicator(dq_ranking['percentile'])
        
        # Main embed
        embed = discord.Embed(
            title=f"🎮 {user.display_name}'s BLCSX Profile",
            color=0x7289DA
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # === DOMINANCE QUOTIENT (Most Important) ===
        embed.add_field(
            name="🏆 **PERFORMANCE SCORE** (Overall Skill)",
            value=f"**{dq:.1f}%** {dq_indicator['emoji']} *{dq_indicator['name']}*\n"
                  f"📊 **Rank #{dq_ranking['rank']}** of {dq_ranking['total']} players\n"
                  f"📈 **{dq_ranking['percentile']:.1f}th percentile**",
            inline=False
        )
        
        # === CORE PERFORMANCE STATS ===
        embed.add_field(
            name="📋 **Core Performance**",
            value=f"🎯 **Games Played:** {player_stats['games_played']}\n"
                  f"🏆 **Win Rate:** {win_rate:.1f}% ({player_stats['wins']}W-{player_stats['losses']}L)\n"
                  f"⭐ **Average Score:** {player_stats.get('avg_score', 0):.0f}",
            inline=True
        )
        
        # === KEY STATS ===
        key_stats = []
        key_stats.append(f"⚽ **Goals/Game:** {player_stats.get('goals_per_game', 0):.2f}")
        key_stats.append(f"🤝 **Assists/Game:** {player_stats.get('assists_per_game', 0):.2f}")
        key_stats.append(f"🛡️ **Saves/Game:** {player_stats.get('saves_per_game', 0):.2f}")
        key_stats.append(f"📊 **Shot %:** {player_stats.get('shot_percentage', 0):.1f}%")
        key_stats.append(f"⚡ **Avg Speed:** {player_stats.get('avg_speed', 0):.0f}")
        
        embed.add_field(
            name="📊 **Key Statistics**",
            value="\n".join(key_stats),
            inline=True
        )
        
        # === PERFORMANCE INDICATORS LEGEND ===
        legend = "🏆 Elite (90%+) | 🥇 Excellent (80%+) | ✅ Good (65%+) | ➖ Average (35-65%) | 📉 Poor (20-35%) | 🔻 Terrible (<20%)"
        embed.add_field(
            name="📖 **Performance Legend**",
            value=legend,
            inline=False
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
            
            # Calculate dominance quotients and update database
            for player_stats in processed_players:
                dominance_quotient = self.calculator.calculate_simple_score(player_stats, processed_players)
                player_stats['dominance_quotient'] = dominance_quotient
                
                # Calculate percentile rank
                all_dqs = [p['dominance_quotient'] for p in processed_players]
                ranking = self.calculator.calculate_ranking(dominance_quotient, all_dqs)
                player_stats['percentile_rank'] = ranking['percentile']
                
                # Update database
                self.db.update_player_statistics(player_stats)
            
            logger.info(f"Processed {len(processed_players)} players successfully")
    
    def extract_player_stats(self, player_data: Dict, season_id: str) -> Dict:
        """Extract and calculate player statistics from API data"""
        try:
            player_id = f"{player_data['platform']}:{player_data['id']}"
            cumulative = player_data.get('cumulative', {})
            game_average = player_data.get('game_average', {})
            
            # Core stats
            core_avg = game_average.get('core', {})
            movement_stats = game_average.get('movement', {})
            demo_stats = game_average.get('demo', {})
            
            return {
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
            
        except Exception as e:
            logger.error(f"Error linking account: {e}")
            embed = discord.Embed(
                title="Error",
                description="Failed to link account. Please try again.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

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

    @discord.slash_command(name="blcs_leaderboard", description="Show the performance score leaderboard")
    async def leaderboard_command(self, ctx, limit: int = 10):
        """Enhanced leaderboard with performance indicators"""
        
        try:
            all_players = self.db.get_all_player_statistics()
            all_mappings = self.db.get_all_player_mappings()
            
            # Create a lookup table for player names
            player_name_map = {m['ballchasing_player_id']: m['discord_username'] for m in all_mappings}
            
            if not all_players:
                embed = discord.Embed(
                    title="No Data",
                    description="No player statistics available yet.",
                    color=discord.Color.orange()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            # Sort by dominance quotient
            sorted_players = sorted(all_players, key=lambda x: x.get('dominance_quotient', 0), reverse=True)
            limited_players = sorted_players[:min(limit, len(sorted_players))]
            
            # Create leaderboard embed
            embed = discord.Embed(
                title="🏆 BLCSX Performance Leaderboard",
                description="Rankings based on overall player performance analysis",
                color=discord.Color.gold()
            )
            
            leaderboard_text = ""
            for i, player in enumerate(limited_players, 1):
                player_id = player['player_id']
                player_name = player_name_map.get(player_id)

                if not player_name:
                    # Fallback for unmapped players: try to show a cleaner name
                    try:
                        player_name = player_id.split(':')[1]
                    except:
                        player_name = player_id

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
                    medal = f"**{i}.**"
                
                leaderboard_text += f"{medal} **{player_name}** {indicator['emoji']}"
                leaderboard_text += f"    ⭐ Avg Score: **{player.get('avg_score', 0):.0f}** | 🏆 DQ: {dq:.1f}% | 🎯 {player['games_played']} games | 📈 {win_rate:.1f}% WR"
            
            embed.add_field(
                name="📊 Rankings",
                value=leaderboard_text,
                inline=False
            )
            
            # Add legend
            legend = "🏆 Elite | 🥇 Excellent | ✅ Good | ➖ Average | 📉 Poor | 🔻 Terrible"
            embed.add_field(
                name="📖 Performance Indicators",
                value=legend,
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

def setup(bot):
    bot.add_cog(BLCSXStatsCog(bot))