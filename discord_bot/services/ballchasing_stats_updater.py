# File: discord_bot/services/ballchasing_stats_updater.py

import aiohttp
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging
from models.player_profile import (
    get_player_profile, create_or_update_profile, 
    update_player_stats, get_all_profiles
)

logger = logging.getLogger(__name__)

class BallchasingStatsUpdater:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://ballchasing.com/api"
        self.headers = {"Authorization": api_key}
        
        # Group ID from your URL
        self.group_id = "blcs-4-qz9e63f182"
        
        # Player name mapping (Discord ID -> Ballchasing name)
        self.player_mapping = {}
    
    async def fetch_group_stats(self) -> Dict:
        """Fetch comprehensive stats from your BLCS group"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get group data with player statistics
                url = f"{self.base_url}/groups/{self.group_id}"
                
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        group_data = await response.json()
                        logger.info(f"✅ Successfully fetched BLCS group data")
                        return group_data
                    else:
                        logger.error(f"❌ Failed to fetch group data: {response.status}")
                        error_text = await response.text()
                        logger.error(f"Error details: {error_text}")
                        return {}
        except Exception as e:
            logger.error(f"❌ Error fetching group stats: {e}")
            return {}
    
    def extract_player_stats(self, group_data: Dict) -> List[Dict]:
        """Extract player stats from group data"""
        players_stats = []
        
        # Get players from group data
        players = group_data.get('players', [])
        
        for player in players:
            try:
                # Get player identifiers
                player_id = player.get('id', {})
                player_name = player.get('name', 'Unknown')
                platform = player_id.get('platform', 'unknown')
                
                # Get cumulative stats
                cumulative = player.get('cumulative', {})
                games_played = cumulative.get('games', 0)
                
                if games_played == 0:
                    continue  # Skip players with no games
                
                # Get core stats
                core_stats = cumulative.get('core', {})
                
                # Calculate per-game averages
                goals_per_game = core_stats.get('goals', 0) / games_played
                assists_per_game = core_stats.get('assists', 0) / games_played
                saves_per_game = core_stats.get('saves', 0) / games_played
                shots_per_game = core_stats.get('shots', 0) / games_played
                score_per_game = core_stats.get('score', 0) / games_played
                
                # Calculate shooting percentage
                total_shots = core_stats.get('shots', 0)
                total_goals = core_stats.get('goals', 0)
                shot_percentage = (total_goals / total_shots * 100) if total_shots > 0 else 0
                
                # Get demo stats
                demo_stats = cumulative.get('demo', {})
                demos_inflicted = demo_stats.get('inflicted', 0)
                demos_taken = demo_stats.get('taken', 0)
                
                # Calculate win percentage
                wins = cumulative.get('wins', 0)
                win_percentage = (wins / games_played * 100) if games_played > 0 else 0
                
                # Get movement stats if available
                movement_stats = cumulative.get('movement', {})
                avg_speed = movement_stats.get('avg_speed', 0)
                
                player_stats = {
                    'name': player_name,
                    'platform': platform,
                    'ballchasing_id': f"{platform}:{player_id.get('id', '')}",
                    
                    # Game counts
                    'games_played': games_played,
                    'wins': wins,
                    'losses': games_played - wins,
                    
                    # Totals
                    'total_goals': core_stats.get('goals', 0),
                    'total_assists': core_stats.get('assists', 0),
                    'total_saves': core_stats.get('saves', 0),
                    'total_shots': core_stats.get('shots', 0),
                    'total_score': core_stats.get('score', 0),
                    
                    # Per-game averages
                    'goals_per_game': goals_per_game,
                    'assists_per_game': assists_per_game,
                    'saves_per_game': saves_per_game,
                    'shots_per_game': shots_per_game,
                    'score_per_game': score_per_game,
                    
                    # Percentages
                    'goal_percentage': shot_percentage,
                    'win_percentage': win_percentage,
                    
                    # Other stats
                    'demos_inflicted': demos_inflicted,
                    'demos_taken': demos_taken,
                    'demos_inflicted_per_game': demos_inflicted / games_played,
                    'demos_taken_per_game': demos_taken / games_played,
                    'avg_speed': avg_speed,
                }
                
                players_stats.append(player_stats)
                logger.info(f"✅ Extracted stats for {player_name}: {games_played} games, {wins} wins")
                
            except Exception as e:
                logger.error(f"❌ Error extracting stats for player: {e}")
                continue
        
        return players_stats
    
    def link_player(self, discord_id: int, ballchasing_name: str):
        """Link a Discord user to their ballchasing name"""
        self.player_mapping[discord_id] = ballchasing_name.lower()
        logger.info(f"✅ Linked Discord {discord_id} to ballchasing '{ballchasing_name}'")
    
    async def update_all_player_profiles(self):
        """Update all linked players with fresh ballchasing data"""
        # Fetch fresh data from ballchasing
        group_data = await self.fetch_group_stats()
        if not group_data:
            logger.error("❌ No group data retrieved, cannot update profiles")
            return
        
        # Extract player stats
        players_stats = self.extract_player_stats(group_data)
        if not players_stats:
            logger.error("❌ No player stats extracted from group data")
            return
        
        # Update profiles for linked players
        updated_count = 0
        
        for discord_id, ballchasing_name in self.player_mapping.items():
            try:
                # Find matching player in ballchasing data
                matching_player = None
                for player_stats in players_stats:
                    if player_stats['name'].lower() == ballchasing_name.lower():
                        matching_player = player_stats
                        break
                
                if matching_player:
                    # Get or create profile
                    profile = get_player_profile(discord_id)
                    
                    if not profile:
                        # Create new profile
                        create_or_update_profile(
                            discord_id,
                            rl_name=matching_player['name'],
                            **self.convert_stats_for_profile(matching_player)
                        )
                        logger.info(f"✅ Created new profile for {matching_player['name']}")
                    else:
                        # Update existing profile
                        update_data = self.convert_stats_for_profile(matching_player)
                        for key, value in update_data.items():
                            if hasattr(profile, key):
                                setattr(profile, key, value)
                        
                        # Update timestamp
                        profile.last_updated = datetime.utcnow()
                        
                        # Save changes (assuming you have a session management system)
                        try:
                            from models.player_profile import Session
                            session = Session()
                            session.merge(profile)
                            session.commit()
                            session.close()
                        except:
                            # Fallback if session management is different
                            create_or_update_profile(discord_id, **update_data)
                        
                        logger.info(f"✅ Updated profile for {matching_player['name']}")
                    
                    updated_count += 1
                else:
                    logger.warning(f"⚠️ No ballchasing data found for '{ballchasing_name}' (Discord ID: {discord_id})")
                    
            except Exception as e:
                logger.error(f"❌ Error updating profile for Discord ID {discord_id}: {e}")
        
        logger.info(f"🎉 Successfully updated {updated_count} player profiles from BLCS data")
        return updated_count
    
    def convert_stats_for_profile(self, ballchasing_stats: Dict) -> Dict:
        """Convert ballchasing stats to profile model format"""
        return {
            'rl_name': ballchasing_stats['name'],
            'games_played': ballchasing_stats['games_played'],
            'wins': ballchasing_stats['wins'],
            'losses': ballchasing_stats['losses'],
            'total_goals': ballchasing_stats['total_goals'],
            'total_assists': ballchasing_stats['total_assists'],
            'total_saves': ballchasing_stats['total_saves'],
            'total_shots': ballchasing_stats['total_shots'],
            'total_score': ballchasing_stats['total_score'],
            'goal_percentage': ballchasing_stats['goal_percentage'],
            'win_percentage': ballchasing_stats['win_percentage'],
            'demos_inflicted': ballchasing_stats['demos_inflicted'],
            'demos_taken': ballchasing_stats['demos_taken'],
            'last_updated': datetime.utcnow()
        }
    
    async def get_live_group_summary(self) -> Dict:
        """Get a summary of the current group stats for display"""
        group_data = await self.fetch_group_stats()
        if not group_data:
            return {}
        
        players_stats = self.extract_player_stats(group_data)
        
        summary = {
            'total_players': len(players_stats),
            'total_games': sum(p['games_played'] for p in players_stats),
            'top_scorer': max(players_stats, key=lambda p: p['total_goals'], default={}),
            'top_saver': max(players_stats, key=lambda p: p['total_saves'], default={}),
            'highest_win_rate': max(players_stats, key=lambda p: p['win_percentage'], default={}),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return summary

# Global instance
ballchasing_updater = None

def initialize_ballchasing_updater(api_key: str):
    """Initialize the global ballchasing updater"""
    global ballchasing_updater
    ballchasing_updater = BallchasingStatsUpdater(api_key)
    return ballchasing_updater

def get_ballchasing_updater():
    """Get the global ballchasing updater instance"""
    return ballchasing_updater

# Helper functions for easy use
async def sync_blcs_stats():
    """Sync all BLCS stats - convenience function"""
    if ballchasing_updater:
        return await ballchasing_updater.update_all_player_profiles()
    return 0

def link_discord_to_blcs(discord_id: int, ballchasing_name: str):
    """Link Discord user to BLCS ballchasing name"""
    if ballchasing_updater:
        ballchasing_updater.link_player(discord_id, ballchasing_name)
        return True
    return False