import requests
import asyncio
from datetime import datetime
from models.player_profile import update_player_stats, get_player_profile
import os

class BallchasingService:
    def __init__(self):
        self.api_key = os.getenv('BALLCHASING_API_KEY')
        self.base_url = "https://ballchasing.com/api"
        self.headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        # Discord ID to ballchasing player mapping
        # You'll populate this as you link players
        self.player_mapping = {}
    
    def get_group_replays(self, group_id, since_date=None):
        """Get replays from a specific ballchasing group"""
        url = f"{self.base_url}/replays"
        params = {
            'group': group_id,
            'count': 200  # Max per request
        }
        
        if since_date:
            params['replay-date-after'] = since_date.isoformat()
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching replays: {e}")
            return None
    
    def get_replay_details(self, replay_id):
        """Get detailed stats for a specific replay"""
        url = f"{self.base_url}/replays/{replay_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching replay {replay_id}: {e}")
            return None
    
    def extract_player_stats(self, replay_data):
        """Extract player stats from replay data"""
        players_stats = []
        
        # Check both teams
        for team_color in ['blue', 'orange']:
            team = replay_data.get(team_color, {})
            players = team.get('players', [])
            
            for player in players:
                player_id = player.get('id', {})
                
                # Try different ID types
                steam_id = player_id.get('id', '')
                platform = player_id.get('platform', '')
                
                # Get core stats
                core_stats = player.get('stats', {}).get('core', {})
                
                player_stats = {
                    'name': player.get('name', ''),
                    'platform': platform,
                    'player_id': steam_id,
                    'team_color': team_color,
                    'won': team.get('stats', {}).get('core', {}).get('goals', 0) > 
                           replay_data.get('orange' if team_color == 'blue' else 'blue', {})
                           .get('stats', {}).get('core', {}).get('goals', 0),
                    
                    # Core stats
                    'goals': core_stats.get('goals', 0),
                    'saves': core_stats.get('saves', 0),
                    'shots': core_stats.get('shots', 0),
                    'score': core_stats.get('score', 0),
                    'assists': core_stats.get('assists', 0),
                    
                    # Additional stats you might want
                    'mvp': core_stats.get('mvp', False),
                    'demos_inflicted': player.get('stats', {}).get('demo', {}).get('inflicted', 0),
                    'demos_taken': player.get('stats', {}).get('demo', {}).get('taken', 0),
                }
                
                players_stats.append(player_stats)
        
        return players_stats
    
    def link_player_to_discord(self, discord_id, ballchasing_name, steam_id=None):
        """Link a Discord user to their ballchasing.com identity"""
        self.player_mapping[ballchasing_name.lower()] = discord_id
        
        # Also update their profile with ballchasing info
        profile_data = {
            'rl_name': ballchasing_name,
            'steam_id': steam_id
        }
        
        from models.player_profile import create_or_update_profile
        create_or_update_profile(discord_id, **profile_data)
        
        print(f"Linked {ballchasing_name} to Discord user {discord_id}")
    
    def process_replay_for_discord_users(self, replay_data):
        """Process a replay and update Discord users' stats"""
        players_stats = self.extract_player_stats(replay_data)
        updated_players = []
        
        for player_stats in players_stats:
            player_name = player_stats['name'].lower()
            
            # Find matching Discord user
            discord_id = self.player_mapping.get(player_name)
            
            if discord_id:
                try:
                    # Update their profile stats
                    update_player_stats(discord_id, player_stats)
                    updated_players.append({
                        'discord_id': discord_id,
                        'name': player_stats['name'],
                        'stats': player_stats
                    })
                    print(f"Updated stats for {player_stats['name']}")
                except Exception as e:
                    print(f"Error updating stats for {player_stats['name']}: {e}")
        
        return updated_players
    
    async def monitor_group_for_updates(self, group_id, check_interval=300):
        """Monitor a ballchasing group for new replays (5 min intervals)"""
        last_check = datetime.now()
        
        while True:
            try:
                print(f"Checking for new replays since {last_check}")
                
                # Get replays since last check
                replays_data = self.get_group_replays(group_id, since_date=last_check)
                
                if replays_data and replays_data.get('list'):
                    new_replays = replays_data['list']
                    print(f"Found {len(new_replays)} new replays")
                    
                    for replay in new_replays:
                        replay_id = replay.get('id')
                        if replay_id:
                            # Get detailed replay data
                            detailed_replay = self.get_replay_details(replay_id)
                            if detailed_replay:
                                # Process for Discord users
                                updated_players = self.process_replay_for_discord_users(detailed_replay)
                                
                                if updated_players:
                                    print(f"Updated {len(updated_players)} Discord users from replay {replay_id}")
                
                last_check = datetime.now()
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            
            # Wait before next check
            await asyncio.sleep(check_interval)

# Global service instance
ballchasing_service = BallchasingService()

# Helper functions for Discord commands
def link_discord_to_ballchasing(discord_id, rl_name, steam_id=None, is_admin=False):
    """Helper to link Discord user to ballchasing identity"""
    # Add a check to ensure only admins can link other users if you want to be specific
    # For now, the check is in the cog, which is sufficient
    return ballchasing_service.link_player_to_discord(discord_id, rl_name, steam_id)

def start_monitoring_group(group_id):
    """Start monitoring a ballchasing group"""
    asyncio.create_task(ballchasing_service.monitor_group_for_updates(group_id))