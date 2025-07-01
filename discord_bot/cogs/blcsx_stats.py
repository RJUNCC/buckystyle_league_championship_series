# cogs/blcsx_stats.py
import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class PlayerMapping(Base):
    __tablename__ = 'player_mappings'
    
    discord_id = Column(BigInteger, primary_key=True)
    discord_username = Column(String(255))
    ballchasing_player_id = Column(String(255))
    ballchasing_platform = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PlayerStatistics(Base):
    __tablename__ = 'player_statistics'
    
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
        async with self.session.get(f"{self.base_url}/groups/{group_id}") as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get group data: {response.status}")
                return {}

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.Session = Session
    
    def add_player_mapping(self, discord_id: int, discord_username: str, 
                          ballchasing_player_id: str, platform: str):
        """Add or update player mapping"""
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
    
    def get_player_mapping(self, discord_id: int) -> Optional[Dict]:
        """Get player mapping by Discord ID"""
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
    
    def update_player_statistics(self, player_stats: Dict):
        """Update player statistics"""
        with self.Session() as session:
            stmt = insert(PlayerStatistics).values(**player_stats)
            stmt = stmt.on_conflict_do_update(
                index_elements=['player_id'],
                set_={
                    'games_played': stmt.excluded.games_played,
                    'wins': stmt.excluded.wins,
                    'losses': stmt.excluded.losses,
                    'avg_score': stmt.excluded.avg_score,
                    'goals_per_game': stmt.excluded.goals_per_game,
                    'assists_per_game': stmt.excluded.assists_per_game,
                    'saves_per_game': stmt.excluded.saves_per_game,
                    'shots_per_game': stmt.excluded.shots_per_game,
                    'shot_percentage': stmt.excluded.shot_percentage,
                    'demos_inflicted_per_game': stmt.excluded.demos_inflicted_per_game,
                    'demos_taken_per_game': stmt.excluded.demos_taken_per_game,
                    'avg_speed': stmt.excluded.avg_speed,
                    'dominance_quotient': stmt.excluded.dominance_quotient,
                    'percentile_rank': stmt.excluded.percentile_rank,
                    'last_updated': datetime.utcnow()
                }
            )
            session.execute(stmt)
            session.commit()
    
    def get_player_statistics(self, player_id: str) -> Optional[Dict]:
        """Get player statistics"""
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
    
    def get_all_player_statistics(self) -> List[Dict]:
        """Get all player statistics for ranking calculations"""
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

class DominanceQuotientCalculator:
    def __init__(self):
        # Statistical component weights (will be optimized based on winning patterns)
        self.stat_weights = {
            'goals_per_game': 0.15,
            'assists_per_game': 0.12,
            'saves_per_game': 0.10,
            'shots_per_game': 0.08,
            'shot_percentage': 0.15,
            'avg_score': 0.20,
            'demos_inflicted_per_game': 0.05,
            'demos_taken_per_game': 0.05,
            'avg_speed': 0.05,
            'win_rate': 0.30
        }
    
    def analyze_winning_patterns(self, all_player_data: List[Dict], team_data: List[Dict]) -> Dict:
        """Analyze what statistics correlate with winning to determine optimal weights"""
        logger.info("Analyzing winning patterns to determine stat importance...")
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(all_player_data)
        
        if df.empty:
            logger.warning("No player data available for analysis")
            return self.stat_weights
        
        # Calculate correlations with win rate
        numeric_columns = ['goals_per_game', 'assists_per_game', 'saves_per_game', 
                          'shots_per_game', 'shot_percentage', 'avg_score',
                          'demos_inflicted_per_game', 'demos_taken_per_game', 'avg_speed']
        
        correlations = {}
        win_rates = df['wins'] / df['games_played']
        
        for col in numeric_columns:
            if col in df.columns:
                correlation = np.corrcoef(df[col], win_rates)[0, 1]
                correlations[col] = abs(correlation) if not np.isnan(correlation) else 0
        
        # Normalize correlations to create weights
        total_correlation = sum(correlations.values())
        if total_correlation > 0:
            for stat in correlations:
                self.stat_weights[stat] = correlations[stat] / total_correlation
        
        # Add team performance factor
        self.stat_weights['win_rate'] = 0.3  # Base weight for individual win rate
        
        logger.info(f"Calculated stat weights: {self.stat_weights}")
        return self.stat_weights
    
    def calculate_dominance_quotient(self, player_stats: Dict, all_players: List[Dict]) -> float:
        """Calculate the Dominance Quotient for a player"""
        if not all_players:
            return 50.0  # Default middle value
        
        # Create DataFrame for percentile calculations
        df = pd.DataFrame(all_players)
        
        # Calculate percentiles for each stat
        percentiles = {}
        stats_to_evaluate = ['goals_per_game', 'assists_per_game', 'saves_per_game',
                           'shots_per_game', 'shot_percentage', 'avg_score',
                           'demos_inflicted_per_game', 'avg_speed']
        
        for stat in stats_to_evaluate:
            if stat in df.columns and stat in player_stats:
                player_value = player_stats[stat]
                percentile = (df[stat] < player_value).sum() / len(df) * 100
                percentiles[stat] = percentile
        
        # Calculate win rate percentile
        win_rate = player_stats.get('wins', 0) / max(player_stats.get('games_played', 1), 1)
        if 'wins' in df.columns and 'games_played' in df.columns:
            all_win_rates = df['wins'] / df['games_played']
            win_rate_percentile = (all_win_rates < win_rate).sum() / len(df) * 100
            percentiles['win_rate'] = win_rate_percentile
        
        # Calculate weighted dominance quotient
        dominance_quotient = 0
        for stat, weight in self.stat_weights.items():
            if stat in percentiles:
                dominance_quotient += percentiles[stat] * weight
        
        # Handle negative demo impact (fewer demos taken is better)
        if 'demos_taken_per_game' in percentiles:
            # Invert percentile for demos taken (lower is better)
            inverted_demo_percentile = 100 - percentiles['demos_taken_per_game']
            dominance_quotient += inverted_demo_percentile * self.stat_weights.get('demos_taken_per_game', 0.05)
        
        # Ensure dominance quotient is between 0 and 100
        return max(0, min(100, dominance_quotient))

class ModernProfileSystem:
    def __init__(self, db: DatabaseManager):
        self.db = db
        
        # Performance indicators
        self.performance_indicators = {
            'elite': {'emoji': '🏆', 'threshold': 90, 'color': 0x4CAF50, 'name': 'ELITE'},
            'excellent': {'emoji': '🥇', 'threshold': 80, 'color': 0x8BC34A, 'name': 'EXCELLENT'},
            'good': {'emoji': '✅', 'threshold': 65, 'color': 0xFFC107, 'name': 'GOOD'},
            'average': {'emoji': '➖', 'threshold': 35, 'color': 0xFF9800, 'name': 'AVERAGE'},
            'poor': {'emoji': '📉', 'threshold': 20, 'color': 0xF44336, 'name': 'POOR'},
            'terrible': {'emoji': '🔻', 'threshold': 0, 'color': 0xB71C1C, 'name': 'TERRIBLE'}
        }
    
    def get_performance_indicator(self, percentile: float) -> Dict:
        """Get performance indicator based on percentile"""
        for level, data in self.performance_indicators.items():
            if percentile >= data['threshold']:
                return data
        return self.performance_indicators['terrible']
    
    def calculate_stat_ranking(self, player_value: float, all_values: List[float], 
                             higher_is_better: bool = True) -> Dict:
        """Calculate ranking and percentile for a stat"""
        if not all_values or len(all_values) <= 1:
            return {'rank': 1, 'total': 1, 'percentile': 50.0}
        
        # Sort values based on whether higher or lower is better
        sorted_values = sorted(all_values, reverse=higher_is_better)
        
        # Find player's rank
        rank = 1
        for i, value in enumerate(sorted_values, 1):
            if (higher_is_better and player_value >= value) or (not higher_is_better and player_value <= value):
                rank = i
                break
        
        # Calculate percentile
        if higher_is_better:
            percentile = (sum(1 for v in all_values if v < player_value) / len(all_values)) * 100
        else:
            percentile = (sum(1 for v in all_values if v > player_value) / len(all_values)) * 100
        
        return {
            'rank': rank,
            'total': len(all_values),
            'percentile': max(0, min(100, percentile))
        }
    
    def create_profile_embed(self, user: discord.User, player_stats: Dict, all_players: List[Dict]) -> discord.Embed:
        """Create modern profile embed with rankings and indicators"""
        
        # Calculate win rate
        win_rate = (player_stats['wins'] / max(player_stats['games_played'], 1)) * 100
        
        # Create DataFrame for easier calculations
        df = pd.DataFrame(all_players)
        
        # Main embed
        embed = discord.Embed(
            title=f"🎮 {user.display_name}'s BLCSX Profile",
            color=0x7289DA
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # === DOMINANCE QUOTIENT (Most Important) ===
        dq = player_stats['dominance_quotient']
        dq_ranking = self.calculate_stat_ranking(dq, [p['dominance_quotient'] for p in all_players])
        dq_indicator = self.get_performance_indicator(dq_ranking['percentile'])
        
        embed.add_field(
            name="🏆 **DOMINANCE QUOTIENT** (Overall Skill)",
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
                  f"⭐ **Percentile Rank:** {player_stats['percentile_rank']:.1f}%",
            inline=True
        )
        
        # === KEY STATS ===
        stat_configs = [
            ('avg_score', 'Average Score', '🎯', True),
            ('goals_per_game', 'Goals per Game', '⚽', True),
            ('assists_per_game', 'Assists per Game', '🤝', True),
            ('saves_per_game', 'Saves per Game', '🛡️', True),
            ('shot_percentage', 'Shot Percentage', '📊', True),
            ('avg_speed', 'Average Speed', '⚡', True)
        ]
        
        key_stats = []
        for stat_key, stat_name, emoji, higher_is_better in stat_configs:
            if stat_key not in df.columns:
                continue
                
            value = player_stats.get(stat_key, 0)
            ranking = self.calculate_stat_ranking(value, df[stat_key].tolist(), higher_is_better)
            indicator = self.get_performance_indicator(ranking['percentile'])
            
            if stat_key == 'shot_percentage':
                value_str = f"{value:.1f}%"
            elif stat_key == 'avg_speed':
                value_str = f"{value:.0f}"
            else:
                value_str = f"{value:.2f}"
            
            key_stats.append(f"{emoji} **{stat_name}:** {value_str} {indicator['emoji']} (#{ranking['rank']})")
        
        embed.add_field(
            name="📊 **Key Statistics**",
            value="\n".join(key_stats),
            inline=False
        )
        
        # === STANDOUT PERFORMANCES ===
        standouts = []
        
        for stat_key, stat_name, emoji, higher_is_better in stat_configs:
            if stat_key not in df.columns:
                continue
                
            value = player_stats.get(stat_key, 0)
            ranking = self.calculate_stat_ranking(value, df[stat_key].tolist(), higher_is_better)
            
            # Top 3 performances
            if ranking['rank'] <= 3:
                if ranking['rank'] == 1:
                    standouts.append(f"🥇 **#1 in {stat_name}**")
                elif ranking['rank'] == 2:
                    standouts.append(f"🥈 **#2 in {stat_name}**")
                elif ranking['rank'] == 3:
                    standouts.append(f"🥉 **#3 in {stat_name}**")
        
        if standouts:
            embed.add_field(
                name="🌟 **Notable Rankings**",
                value="\n".join(standouts[:4]),
                inline=False
            )
        
        # === PERFORMANCE INDICATORS LEGEND ===
        legend = "🏆 Elite (90%+) | 🥇 Excellent (80%+) | ✅ Good (65%+) | ➖ Average (35-65%) | 📉 Poor (20-35%) | 🔻 Terrible (<20%)"
        embed.add_field(
            name="📖 **Performance Legend**",
            value=legend,
            inline=False
        )
        
        embed.set_footer(text=f"Last updated: {player_stats.get('last_updated', 'Unknown')} | BLCSX Season 4")
        
        return embed

class DataProcessor:
    def __init__(self, api: BallchasingAPI, db: DatabaseManager, calculator: DominanceQuotientCalculator):
        self.api = api
        self.db = db
        self.calculator = calculator
    
    async def process_group_data(self, group_id: str, season_id: str = "BLCS4"):
        """Process all data from a ballchasing group"""
        logger.info(f"Processing group data for {group_id}")
        
        # Get group data
        group_data = await self.api.get_group_data(group_id)
        if not group_data:
            logger.error("Failed to get group data")
            return
        
        # Extract player and team data
        players_data = group_data.get('players', [])
        teams_data = group_data.get('teams', [])
        
        logger.info(f"Found {len(players_data)} players and {len(teams_data)} teams")
        
        # Process individual player statistics
        processed_players = []
        for player in players_data:
            player_stats = self.extract_player_stats(player, season_id)
            if player_stats:
                processed_players.append(player_stats)
        
        # Analyze winning patterns and calculate weights
        self.calculator.analyze_winning_patterns(processed_players, teams_data)
        
        # Calculate dominance quotients and update database
        for player_stats in processed_players:
            dominance_quotient = self.calculator.calculate_dominance_quotient(player_stats, processed_players)
            player_stats['dominance_quotient'] = dominance_quotient
            
            # Calculate percentile rank
            all_dqs = [p['dominance_quotient'] for p in processed_players]
            percentile_rank = self.calculator.calculate_percentile(dominance_quotient, all_dqs)
            player_stats['percentile_rank'] = percentile_rank
            
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
            core_stats = cumulative.get('core', {})
            core_avg = game_average.get('core', {})
            
            # Movement stats for average speed
            movement_stats = game_average.get('movement', {})
            
            # Demo stats
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
                'dominance_quotient': 0,  # Will be calculated
                'percentile_rank': 0  # Will be calculated
            }
        except Exception as e:
            logger.error(f"Error extracting player stats: {e}")
            return None

class BLCSXStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Get ballchasing API token from environment
        ballchasing_token = os.getenv('BALLCHASING_API_KEY')
        if not ballchasing_token:
            raise ValueError("BALLCHASING_API_KEY environment variable not set")
        
        self.ballchasing_token = ballchasing_token
        self.db = DatabaseManager(database_url)
        self.calculator = DominanceQuotientCalculator()
        self.profile_system = ModernProfileSystem(self.db)
        
        logger.info("BLCSX Stats Cog initialized")

    @discord.slash_command(name="blcs_profile", description="Show comprehensive BLCSX player profile with rankings")
    @discord.app_commands.describe(player="The player to show profile for (leave empty for yourself)")
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
            embed = self.profile_system.create_profile_embed(target_user, player_stats, all_players)
            
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
    @discord.app_commands.describe(
        player_id="Your ballchasing.com player ID (e.g., steam:76561198123456789)",
        platform="Your platform (steam, epic, ps4, xbox, switch)"
    )
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

    @discord.slash_command(name="blcs_update", description="Update player statistics from ballchasing.com (Admin only)")
    @discord.app_commands.describe(group_id="The ballchasing.com group ID to process")
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
            async with BallchasingAPI(self.ballchasing_token) as api:
                processor = DataProcessor(api, self.db, self.calculator)
                
                # Process the group data
                await processor.process_group_data(group_id)
                
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

    @discord.slash_command(name="blcs_leaderboard", description="Show the dominance quotient leaderboard")
    @discord.app_commands.describe(limit="Number of players to show (default 10)")
    async def leaderboard_command(self, ctx, limit: int = 10):
        """Enhanced leaderboard with performance indicators"""
        
        try:
            all_players = self.db.get_all_player_statistics()
            
            if not all_players:
                embed = discord.Embed(
                    title="No Data",
                    description="No player statistics available yet.",
                    color=discord.Color.orange()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            # Limit the results
            limited_players = all_players[:min(limit, len(all_players))]
            
            # Create leaderboard embed
            embed = discord.Embed(
                title="🏆 BLCSX Dominance Quotient Leaderboard",
                description="Rankings based on overall player performance analysis",
                color=discord.Color.gold()
            )
            
            leaderboard_text = ""
            for i, player in enumerate(limited_players, 1):
                # Extract player name from player_id
                player_name = player['player_id'].split(':')[1] if ':' in player['player_id'] else player['player_id']
                dq = player['dominance_quotient']
                win_rate = (player['wins'] / max(player['games_played'], 1)) * 100
                
                # Get performance indicator
                indicator = self.profile_system.get_performance_indicator(dq)
                
                # Medal for top 3
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"**{i}.**"
                
                leaderboard_text += f"{medal} **{player_name}** {indicator['emoji']}\n"
                leaderboard_text += f"    🏆 DQ: {dq:.1f}% | 🎯 {player['games_played']} games | 📈 {win_rate:.1f}% WR\n\n"
            
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
                description="Failed to generate leaderboard.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

    @discord.slash_command(name="blcs_stat_leaders", description="Show leaders in specific stats")
    @discord.app_commands.describe(stat="Choose which stat to rank by", limit="Number of players to show (default 5)")
    @discord.app_commands.choices(stat=[
        discord.app_commands.Choice(name="Goals per Game", value="goals_per_game"),
        discord.app_commands.Choice(name="Assists per Game", value="assists_per_game"),
        discord.app_commands.Choice(name="Saves per Game", value="saves_per_game"),
        discord.app_commands.Choice(name="Average Score", value="avg_score"),
        discord.app_commands.Choice(name="Shot Percentage", value="shot_percentage"),
        discord.app_commands.Choice(name="Average Speed", value="avg_speed"),
        discord.app_commands.Choice(name="Demos Inflicted", value="demos_inflicted_per_game")
    ])
    async def stat_leaders_command(self, ctx, stat: str, limit: int = 5):
        """Show leaders in specific statistics"""
        
        try:
            all_players = self.db.get_all_player_statistics()
            
            if not all_players:
                embed = discord.Embed(
                    title="No Data",
                    description="No player statistics available yet.",
                    color=discord.Color.orange()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            # Sort by the selected stat
            stat_name_map = {
                'goals_per_game': 'Goals per Game',
                'assists_per_game': 'Assists per Game',
                'saves_per_game': 'Saves per Game',
                'avg_score': 'Average Score',
                'shot_percentage': 'Shot Percentage',
                'avg_speed': 'Average Speed',
                'demos_inflicted_per_game': 'Demos Inflicted per Game'
            }
            
            stat_emoji_map = {
                'goals_per_game': '⚽',
                'assists_per_game': '🤝',
                'saves_per_game': '🛡️',
                'avg_score': '🎯',
                'shot_percentage': '📊',
                'avg_speed': '⚡',
                'demos_inflicted_per_game': '💥'
            }
            
            sorted_players = sorted(all_players, key=lambda x: x[stat], reverse=True)
            limited_players = sorted_players[:min(limit, len(sorted_players))]
            
            stat_display_name = stat_name_map.get(stat, stat)
            stat_emoji = stat_emoji_map.get(stat, '📈')
            
            embed = discord.Embed(
                title=f"{stat_emoji} {stat_display_name} Leaders",
                description=f"Top performers in {stat_display_name.lower()}",
                color=0x4CAF50
            )
            
            leaders_text = ""
            for i, player in enumerate(limited_players, 1):
                player_name = player['player_id'].split(':')[1] if ':' in player['player_id'] else player['player_id']
                value = player[stat]
                
                # Format value appropriately
                if stat == 'shot_percentage':
                    value_str = f"{value:.1f}%"
                elif stat == 'avg_speed':
                    value_str = f"{value:.0f}"
                else:
                    value_str = f"{value:.2f}"
                
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"**{i}.**"
                
                leaders_text += f"{medal} **{player_name}**: {value_str}\n"
            
            embed.add_field(
                name="🏆 Top Performers",
                value=leaders_text,
                inline=False
            )
            
            await ctx.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stat leaders command: {e}")
            embed = discord.Embed(
                title="Error",
                description="Failed to generate stat leaders.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

    @discord.slash_command(name="blcs_compare", description="Compare two players head-to-head")
    async def compare_command(self, ctx, player1: discord.Member, player2: discord.Member):
        """Compare two players head-to-head"""
        
        try:
            # Get both players' mappings
            mapping1 = self.db.get_player_mapping(player1.id)
            mapping2 = self.db.get_player_mapping(player2.id)
            
            if not mapping1:
                embed = discord.Embed(
                    title="Player Not Found",
                    description=f"No ballchasing.com mapping found for {player1.display_name}.",
                    color=discord.Color.red()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            if not mapping2:
                embed = discord.Embed(
                    title="Player Not Found",
                    description=f"No ballchasing.com mapping found for {player2.display_name}.",
                    color=discord.Color.red()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            # Get both players' statistics
            stats1 = self.db.get_player_statistics(mapping1['ballchasing_player_id'])
            stats2 = self.db.get_player_statistics(mapping2['ballchasing_player_id'])
            
            if not stats1 or not stats2:
                embed = discord.Embed(
                    title="Statistics Not Found",
                    description="Player statistics not found for one or both players.",
                    color=discord.Color.orange()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"⚔️ {player1.display_name} vs {player2.display_name}",
                description="Head-to-head player comparison",
                color=0xFF6B6B
            )
            
            # Compare key stats
            comparison_stats = [
                ('dominance_quotient', 'Dominance Quotient', '%'),
                ('avg_score', 'Average Score', ''),
                ('goals_per_game', 'Goals per Game', ''),
                ('assists_per_game', 'Assists per Game', ''),
                ('saves_per_game', 'Saves per Game', ''),
                ('shot_percentage', 'Shot Percentage', '%')
            ]
            
            comparison_text = ""
            wins1 = 0
            wins2 = 0
            
            for stat_key, stat_name, unit in comparison_stats:
                val1 = stats1.get(stat_key, 0)
                val2 = stats2.get(stat_key, 0)
                
                if val1 > val2:
                    winner = "🔵"
                    loser = "🔴"
                    wins1 += 1
                elif val2 > val1:
                    winner = "🔴"
                    loser = "🔵"
                    wins2 += 1
                else:
                    winner = loser = "🟡"
                
                comparison_text += f"**{stat_name}:**\n"
                comparison_text += f"{winner} {player1.display_name}: {val1:.2f}{unit}\n"
                comparison_text += f"{loser} {player2.display_name}: {val2:.2f}{unit}\n\n"
            
            embed.add_field(
                name="📊 Statistical Comparison",
                value=comparison_text,
                inline=False
            )
            
            # Overall summary
            if wins1 > wins2:
                summary = f"🔵 **{player1.display_name}** leads in {wins1} categories"
            elif wins2 > wins1:
                summary = f"🔴 **{player2.display_name}** leads in {wins2} categories"
            else:
                summary = "🟡 **Even match** - tied performance"
            
            embed.add_field(
                name="🏆 Overall Comparison",
                value=summary,
                inline=False
            )
            
            await ctx.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in compare command: {e}")
            embed = discord.Embed(
                title="Error",
                description="Failed to compare players.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

    @discord.slash_command(name="blcs_quickstats", description="Show condensed player statistics")
    @discord.app_commands.describe(player="The player to show stats for (leave empty for yourself)")
    async def quick_stats_command(self, ctx, player: discord.Member = None):
        """Quick stats overview"""
        target_user = player or ctx.author
        
        try:
            # Get player mapping
            mapping = self.db.get_player_mapping(target_user.id)
            if not mapping:
                embed = discord.Embed(
                    title="Player Not Found",
                    description=f"No ballchasing.com mapping found for {target_user.display_name}.\nUse `/blcs_link` to connect your account.",
                    color=discord.Color.red()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            # Get player statistics
            player_stats = self.db.get_player_statistics(mapping['ballchasing_player_id'])
            if not player_stats:
                embed = discord.Embed(
                    title="No Statistics",
                    description=f"No statistics found for {target_user.display_name}.",
                    color=discord.Color.orange()
                )
                await ctx.response.send_message(embed=embed)
                return
            
            # Get all players for comparison
            all_players = self.db.get_all_player_statistics()
            
            # Create quick stats embed
            dq = player_stats['dominance_quotient']
            dq_ranking = self.profile_system.calculate_stat_ranking(dq, [p['dominance_quotient'] for p in all_players])
            dq_indicator = self.profile_system.get_performance_indicator(dq_ranking['percentile'])
            
            win_rate = (player_stats['wins'] / max(player_stats['games_played'], 1)) * 100
            
            embed = discord.Embed(
                title=f"⚡ {target_user.display_name} - Quick Stats",
                description=f"🏆 **Dominance Quotient: {dq:.1f}%** {dq_indicator['emoji']} (#{dq_ranking['rank']}/{dq_ranking['total']})\n"
                           f"🎯 **{player_stats['games_played']} games** | **{win_rate:.1f}% win rate**",
                color=dq_indicator['color']
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Top 4 stats
            df = pd.DataFrame(all_players)
            top_stats = []
            
            stat_configs = [
                ('goals_per_game', 'Goals/Game', '⚽'),
                ('assists_per_game', 'Assists/Game', '🤝'),
                ('saves_per_game', 'Saves/Game', '🛡️'),
                ('avg_score', 'Avg Score', '🎯')
            ]
            
            for stat_key, stat_name, emoji in stat_configs:
                if stat_key in df.columns:
                    value = player_stats.get(stat_key, 0)
                    ranking = self.profile_system.calculate_stat_ranking(value, df[stat_key].tolist())
                    top_stats.append(f"{emoji} {stat_name}: **{value:.1f}** (#{ranking['rank']})")
            
            embed.add_field(
                name="📊 Key Stats",
                value="\n".join(top_stats[:4]),
                inline=False
            )
            
            await ctx.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in quick stats command: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred while generating quick stats.",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed)

def setup(bot):
    bot.add_cog(BLCSXStatsCog(bot))