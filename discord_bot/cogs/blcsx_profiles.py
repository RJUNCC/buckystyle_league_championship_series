# File: discord_bot/cogs/blcsx_profiles.py

import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Optional, Tuple
import math
from datetime import datetime
import logging
import os
from models.player_profile import (
    get_player_profile, create_or_update_profile, 
    get_all_profiles, update_player_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DominanceQuotientCalculator:
    def __init__(self):
        # Weights determined from analysis of winning patterns
        self.stat_weights = {
            'goals_per_game': 0.15,
            'assists_per_game': 0.12,
            'saves_per_game': 0.18,
            'shots_per_game': 0.10,
            'shot_percentage': 0.13,
            'avg_score': 0.20,
            'demos_inflicted_per_game': 0.05,
            'avg_speed': 0.07
        }
    
    def analyze_winning_patterns(self, all_player_data: List[Dict]) -> Dict:
        """Analyze what stats correlate with winning"""
        logger.info("Analyzing winning patterns...")
        
        if not all_player_data:
            return self.stat_weights
        
        try:
            # Convert to DataFrame for analysis
            df = pd.DataFrame(all_player_data)
            
            # Calculate win rates
            win_rates = []
            for player in all_player_data:
                if player.get('games_played', 0) > 0:
                    win_rate = player.get('wins', 0) / player['games_played']
                    win_rates.append(win_rate)
                else:
                    win_rates.append(0)
            
            # Calculate correlations with win rate
            correlations = {}
            for stat in ['goals_per_game', 'assists_per_game', 'saves_per_game', 'shots_per_game', 
                        'shot_percentage', 'avg_score']:
                if len(df) > 1 and stat in df.columns:
                    try:
                        stat_values = [p.get(stat, 0) for p in all_player_data]
                        if len(stat_values) == len(win_rates) and len(set(stat_values)) > 1:
                            correlation = np.corrcoef(stat_values, win_rates)[0, 1]
                            correlations[stat] = abs(correlation) if not np.isnan(correlation) else 0
                        else:
                            correlations[stat] = 0
                    except Exception as e:
                        logger.warning(f"Error calculating correlation for {stat}: {e}")
                        correlations[stat] = 0
            
            # Normalize to create weights
            total = sum(correlations.values())
            if total > 0:
                for stat in correlations:
                    self.stat_weights[stat] = correlations[stat] / total
            
            logger.info(f"Calculated weights: {self.stat_weights}")
            return self.stat_weights
            
        except Exception as e:
            logger.error(f"Error in analyze_winning_patterns: {e}")
            return self.stat_weights
    
    def calculate_dominance_quotient(self, player_stats: Dict, all_players: List[Dict]) -> float:
        """Calculate Dominance Quotient based on percentile rankings"""
        if not all_players or len(all_players) <= 1:
            return 50.0
        
        try:
            # Calculate percentiles for each stat
            percentiles = {}
            for stat in self.stat_weights.keys():
                if stat in player_stats:
                    player_value = player_stats.get(stat, 0)
                    all_values = [p.get(stat, 0) for p in all_players if p.get(stat) is not None]
                    
                    if len(all_values) > 1:
                        percentile = (sum(1 for v in all_values if v < player_value) / len(all_values)) * 100
                        percentiles[stat] = percentile
                    else:
                        percentiles[stat] = 50
            
            # Calculate weighted dominance quotient
            dominance_quotient = 0
            total_weight = 0
            for stat, weight in self.stat_weights.items():
                if stat in percentiles:
                    dominance_quotient += percentiles[stat] * weight
                    total_weight += weight
            
            if total_weight > 0:
                dominance_quotient = dominance_quotient / total_weight
            
            return max(0, min(100, dominance_quotient))
            
        except Exception as e:
            logger.error(f"Error calculating dominance quotient: {e}")
            return 50.0

class BLCSXProfileCardGenerator:
    def __init__(self):
        self.card_width = 1200
        self.card_height = 800
    
    async def download_discord_avatar(self, user: discord.User) -> Image.Image:
        """Download Discord avatar"""
        try:
            avatar_url = user.display_avatar.url
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as response:
                    if response.status == 200:
                        avatar_data = await response.read()
                        avatar_img = Image.open(io.BytesIO(avatar_data))
                        return avatar_img.resize((150, 150))
        except Exception as e:
            logger.error(f"Failed to download avatar: {e}")
        
        # Default avatar
        img = Image.new('RGB', (150, 150), color='#7289da')
        draw = ImageDraw.Draw(img)
        try:
            font = self.get_font(24)
        except:
            font = ImageFont.load_default()
        draw.text((75, 75), "RL", fill='white', anchor='mm', font=font)
        return img
    
    def get_font(self, size: int):
        """Get font with fallback"""
        try:
            # Try different font paths
            font_paths = [
                "arial.ttf",
                "Arial.ttf", 
                "/System/Library/Fonts/Arial.ttf",  # macOS
                "/Windows/Fonts/arial.ttf",         # Windows
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
            ]
            
            for font_path in font_paths:
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
                    
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def get_stat_color(self, percentile: float) -> str:
        """Get color based on percentile"""
        if percentile >= 80:
            return '#4CAF50'  # Green - Elite
        elif percentile >= 65:
            return '#8BC34A'  # Light Green - Above Average
        elif percentile >= 45:
            return '#FFC107'  # Yellow - Average
        elif percentile >= 25:
            return '#FF9800'  # Orange - Below Average
        else:
            return '#F44336'  # Red - Poor
    
    def calculate_percentile(self, value: float, all_values: List[float]) -> float:
        """Calculate percentile"""
        if not all_values or len(all_values) <= 1:
            return 50.0
        try:
            return (sum(1 for v in all_values if v < value) / len(all_values)) * 100
        except:
            return 50.0
    
    def create_radar_chart(self, radar_stats: List[float]) -> Image.Image:
        """Create radar chart for skill visualization"""
        try:
            fig, ax = plt.subplots(figsize=(4, 4), subplot_kw=dict(projection='polar'))
            fig.patch.set_facecolor('white')
            
            categories = ['Avg Score', 'Goals/Game', 'Assists/Game', 'Saves/Game', 'Shots/Game', 'Shot %']
            N = len(categories)
            
            angles = [n / float(N) * 2 * np.pi for n in range(N)]
            angles += angles[:1]
            
            values = radar_stats + radar_stats[:1]
            
            ax.plot(angles, values, 'o-', linewidth=3, color='#4CAF50', markersize=6)
            ax.fill(angles, values, alpha=0.25, color='#4CAF50')
            
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=10)
            ax.set_ylim(0, 100)
            ax.set_yticks([25, 50, 75, 100])
            ax.set_yticklabels(['25', '50', '75', '100'], fontsize=8)
            ax.grid(True, alpha=0.3)
            ax.set_rlabel_position(0)
            
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            plt.close()
            
            radar_img = Image.open(buffer)
            return radar_img.resize((350, 350))
            
        except Exception as e:
            logger.error(f"Error creating radar chart: {e}")
            # Return placeholder image
            img = Image.new('RGB', (350, 350), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((175, 175), "Radar Chart\nUnavailable", fill='black', anchor='mm')
            return img
    
    async def generate_blcsx_profile_card(self, user: discord.User, profile: Dict, 
                                        all_profiles: List[Dict], guild: discord.Guild = None) -> io.BytesIO:
        """Generate BLCSX style profile card"""
        try:
            img = Image.new('RGB', (self.card_width, self.card_height), 'white')
            draw = ImageDraw.Draw(img)
            
            # Fonts
            title_font = self.get_font(36)
            stat_font = self.get_font(24)
            label_font = self.get_font(18)
            small_font = self.get_font(14)
            
            # Header with BLCSX branding
            draw.rectangle([0, 0, self.card_width, 80], fill='#2C2F33')
            draw.text((20, 25), "BLCSX Player Profile", font=stat_font, fill='white')
            
            # User avatar
            user_avatar = await self.download_discord_avatar(user)
            img.paste(user_avatar, (20, 90))
            
            # Player name and info
            draw.text((200, 100), user.display_name, font=title_font, fill='black')
            
            # RL Name if different
            if profile.get('rl_name') and profile['rl_name'] != user.display_name:
                draw.text((200, 140), f"RL: {profile['rl_name']}", font=label_font, fill='#666666')
            
            # Server icon placeholder (top right)
            draw.rectangle([self.card_width - 80, 10, self.card_width - 20, 70], fill='#7289da')
            draw.text((self.card_width - 50, 40), "BLCSX", font=small_font, fill='white', anchor='mm')
            
            # Calculate Dominance Quotient
            calculator = DominanceQuotientCalculator()
            
            # Convert profile data for dominance calculation
            games_played = max(profile.get('games_played', 1), 1)
            player_data = {
                'goals_per_game': profile.get('total_goals', 0) / games_played,
                'assists_per_game': profile.get('total_assists', 0) / games_played,
                'saves_per_game': profile.get('total_saves', 0) / games_played,
                'shots_per_game': profile.get('total_shots', 0) / games_played,
                'shot_percentage': profile.get('goal_percentage', 0),
                'avg_score': profile.get('total_score', 0) / games_played,
                'games_played': profile.get('games_played', 0),
                'wins': profile.get('wins', 0)
            }
            
            # Convert all profiles for comparison
            all_player_data = []
            for p in all_profiles:
                if p.get('games_played', 0) > 0:
                    all_player_data.append({
                        'goals_per_game': p.get('total_goals', 0) / p['games_played'],
                        'assists_per_game': p.get('total_assists', 0) / p['games_played'],
                        'saves_per_game': p.get('total_saves', 0) / p['games_played'],
                        'shots_per_game': p.get('total_shots', 0) / p['games_played'],
                        'shot_percentage': p.get('goal_percentage', 0),
                        'avg_score': p.get('total_score', 0) / p['games_played'],
                        'games_played': p.get('games_played', 0),
                        'wins': p.get('wins', 0)
                    })
            
            # Calculate dominance quotient
            dominance_quotient = calculator.calculate_dominance_quotient(player_data, all_player_data)
            
            # Main Dominance Quotient display
            main_color = self.get_stat_color(dominance_quotient)
            draw.rectangle([50, 270, 300, 370], fill=main_color)
            draw.text((175, 320), f"{dominance_quotient:.0f}%", font=title_font, fill='white', anchor='mm')
            draw.text((50, 380), "Dominance Quotient", font=label_font, fill='black')
            
            # Stats boxes
            stats_data = [
                ("Avg Score", player_data['avg_score']),
                ("Goals/Game", player_data['goals_per_game']),
                ("Assists/Game", player_data['assists_per_game']),
                ("Saves/Game", player_data['saves_per_game']),
                ("Shots/Game", player_data['shots_per_game']),
                ("Shot %", player_data['shot_percentage']),
                ("Games", profile.get('games_played', 0)),
                ("Win Rate", profile.get('win_percentage', 0)),
                ("Total Score", profile.get('total_score', 0))
            ]
            
            # Draw stats grid
            box_width = 150
            box_height = 60
            start_x = 50
            start_y = 450
            
            for i, (stat_name, value) in enumerate(stats_data):
                row = i // 3
                col = i % 3
                x = start_x + col * (box_width + 20)
                y = start_y + row * (box_height + 30)
                
                # Calculate percentile for coloring
                if stat_name == "Win Rate":
                    all_values = [p.get('win_percentage', 0) for p in all_profiles]
                elif stat_name == "Games":
                    all_values = [p.get('games_played', 0) for p in all_profiles]
                elif stat_name == "Total Score":
                    all_values = [p.get('total_score', 0) for p in all_profiles]
                else:
                    # Map to player_data keys
                    stat_key = stat_name.lower().replace('/', '_').replace(' ', '_')
                    all_values = [p.get(stat_key, 0) for p in all_player_data]
                
                percentile = self.calculate_percentile(value, all_values)
                color = self.get_stat_color(percentile)
                
                # Draw box
                draw.rectangle([x, y, x + box_width, y + box_height], fill=color)
                
                # Format value display
                if stat_name in ["Games", "Total Score"]:
                    value_text = f"{value:.0f}"
                elif stat_name == "Win Rate":
                    value_text = f"{value:.1f}%"
                else:
                    value_text = f"{value:.1f}"
                
                draw.text((x + box_width//2, y + box_height//2), value_text, 
                         font=stat_font, fill='white', anchor='mm')
                draw.text((x, y + box_height + 5), stat_name, font=small_font, fill='black')
            
            # Radar chart
            radar_values = []
            for stat in ['avg_score', 'goals_per_game', 'assists_per_game', 'saves_per_game', 'shots_per_game', 'shot_percentage']:
                if all_player_data:
                    all_values = [p.get(stat, 0) for p in all_player_data]
                    percentile = self.calculate_percentile(player_data.get(stat, 0), all_values)
                else:
                    percentile = 50
                radar_values.append(min(100, max(0, percentile)))
            
            radar_chart = self.create_radar_chart(radar_values)
            img.paste(radar_chart, (700, 200))
            draw.text((875, 180), "Skill Radar", font=label_font, fill='black', anchor='mm')
            
            # Legend
            legend_y = 720
            legend_items = [
                ("Elite (80%+)", '#4CAF50'),
                ("Above Avg (65%+)", '#8BC34A'),
                ("Average (45%+)", '#FFC107'),
                ("Below Avg (25%+)", '#FF9800'),
                ("Poor (<25%)", '#F44336')
            ]
            
            for i, (label, color) in enumerate(legend_items):
                x_pos = 50 + (i * 200)
                draw.rectangle([x_pos, legend_y, x_pos + 20, legend_y + 20], fill=color)
                draw.text((x_pos + 30, legend_y + 10), label, font=small_font, fill='black', anchor='lm')
            
            # Player info section
            info_y = 180
            info_text = f"Games: {profile.get('games_played', 0)} | W: {profile.get('wins', 0)} L: {profile.get('losses', 0)}"
            if profile.get('rank_name'):
                info_text += f" | Rank: {profile['rank_name']}"
                if profile.get('rank_division'):
                    info_text += f" {profile['rank_division']}"
            
            draw.text((200, info_y), info_text, font=small_font, fill='#666666')
            
            # Footer
            footer_text = f"Last updated: {datetime.now().strftime('%m/%d/%Y %H:%M')}"
            draw.text((50, self.card_height - 30), footer_text, font=small_font, fill='#999999')
            
            # Save to buffer
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', quality=95)
            buffer.seek(0)
            
            return buffer
            
        except Exception as e:
            logger.error(f"Error generating profile card: {e}")
            # Return error image
            img = Image.new('RGB', (400, 200), 'white')
            draw = ImageDraw.Draw(img)
            draw.text((200, 100), "Error generating\nprofile card", fill='black', anchor='mm')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            return buffer

class BLCSXProfilesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.calculator = DominanceQuotientCalculator()
        self.profile_generator = BLCSXProfileCardGenerator()

    @discord.slash_command(name="blcsx_profile", description="Show BLCSX style profile card with Dominance Quotient")
    async def blcsx_profile(self, ctx, player: discord.Member = None):
        """Display BLCSX style profile card"""
        
        target_user = player if player else ctx.author
        
        # Get profile from database
        profile = get_player_profile(target_user.id)
        
        if not profile:
            embed = discord.Embed(
                title="❌ Profile Not Found",
                description=f"{'You haven\'t' if target_user == ctx.author else f'{target_user.display_name} hasn\'t'} set up a profile yet!\n\n"
                           f"**Get Started:**\n• Use `/setup_profile` to create your profile\n• Use `/link_ballchasing` to auto-sync stats",
                color=0xff0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        await ctx.response.defer()
        
        try:
            # Get all profiles for comparison
            all_profiles = get_all_profiles()
            
            # Convert profile to dict if needed
            if hasattr(profile, '__dict__'):
                profile_dict = profile.__dict__
            else:
                profile_dict = dict(profile)
            
            # Convert all profiles to dicts
            all_profiles_dicts = []
            for p in all_profiles:
                if hasattr(p, '__dict__'):
                    all_profiles_dicts.append(p.__dict__)
                else:
                    all_profiles_dicts.append(dict(p))
            
            # Generate BLCSX profile card
            card_buffer = await self.profile_generator.generate_blcsx_profile_card(
                target_user, profile_dict, all_profiles_dicts, ctx.guild
            )
            
            # Calculate dominance quotient for embed
            games_played = max(profile_dict.get('games_played', 1), 1)
            player_data = {
                'goals_per_game': profile_dict.get('total_goals', 0) / games_played,
                'assists_per_game': profile_dict.get('total_assists', 0) / games_played,
                'saves_per_game': profile_dict.get('total_saves', 0) / games_played,
                'shots_per_game': profile_dict.get('total_shots', 0) / games_played,
                'shot_percentage': profile_dict.get('goal_percentage', 0),
                'avg_score': profile_dict.get('total_score', 0) / games_played,
                'games_played': profile_dict.get('games_played', 0),
                'wins': profile_dict.get('wins', 0)
            }
            
            all_player_data = []
            for p in all_profiles_dicts:
                if p.get('games_played', 0) > 0:
                    all_player_data.append({
                        'goals_per_game': p.get('total_goals', 0) / p['games_played'],
                        'assists_per_game': p.get('total_assists', 0) / p['games_played'],
                        'saves_per_game': p.get('total_saves', 0) / p['games_played'],
                        'shots_per_game': p.get('total_shots', 0) / p['games_played'],
                        'shot_percentage': p.get('goal_percentage', 0),
                        'avg_score': p.get('total_score', 0) / p['games_played'],
                        'games_played': p.get('games_played', 0),
                        'wins': p.get('wins', 0)
                    })
            
            dominance_quotient = self.calculator.calculate_dominance_quotient(player_data, all_player_data)
            
            # Calculate rank
            all_dominance = []
            for p in all_player_data:
                dq = self.calculator.calculate_dominance_quotient(p, all_player_data)
                all_dominance.append(dq)
            
            rank = len([dq for dq in all_dominance if dq > dominance_quotient]) + 1
            
            # Create embed
            embed = discord.Embed(
                title=f"🎮 {target_user.display_name}'s BLCSX Profile",
                description=f"**Dominance Quotient:** {dominance_quotient:.1f}%\n"
                           f"**League Rank:** #{rank} of {len(all_player_data)}",
                color=0x4CAF50 if dominance_quotient >= 70 else 0xFFC107 if dominance_quotient >= 45 else 0xF44336
            )
            
            embed.set_footer(text="BLCSX Profile • Colors based on percentile rankings")
            
            # Send card
            file = discord.File(card_buffer, filename=f"{target_user.display_name}_blcsx_profile.png")
            await ctx.followup.send(embed=embed, file=file)
            
        except Exception as e:
            logger.error(f"Error generating BLCSX profile: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to generate BLCSX profile card. Please try again.",
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="dominance_leaderboard", description="Show Dominance Quotient leaderboard")
    async def dominance_leaderboard(self, ctx, limit: int = 10):
        """Show dominance quotient leaderboard"""
        
        profiles = get_all_profiles()
        
        if not profiles:
            await ctx.respond("❌ No profiles found in the database.", ephemeral=True)
            return
        
        # Calculate dominance quotients for all players
        all_player_data = []
        player_dominance = []
        
        for profile in profiles:
            if hasattr(profile, '__dict__'):
                profile_dict = profile.__dict__
            else:
                profile_dict = dict(profile)
            
            if profile_dict.get('games_played', 0) > 0:
                games_played = profile_dict['games_played']
                player_data = {
                    'goals_per_game': profile_dict.get('total_goals', 0) / games_played,
                    'assists_per_game': profile_dict.get('total_assists', 0) / games_played,
                    'saves_per_game': profile_dict.get('total_saves', 0) / games_played,
                    'shots_per_game': profile_dict.get('total_shots', 0) / games_played,
                    'shot_percentage': profile_dict.get('goal_percentage', 0),
                    'avg_score': profile_dict.get('total_score', 0) / games_played,
                    'games_played': profile_dict.get('games_played', 0),
                    'wins': profile_dict.get('wins', 0)
                }
                all_player_data.append(player_data)
                player_dominance.append((profile_dict, player_data))
        
        # Calculate dominance quotients
        leaderboard_data = []
        for profile_dict, player_data in player_dominance:
            dominance_quotient = self.calculator.calculate_dominance_quotient(player_data, all_player_data)
            leaderboard_data.append((profile_dict, dominance_quotient))
        
        # Sort by dominance quotient
        leaderboard_data.sort(key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="🏆 BLCSX Dominance Quotient Leaderboard",
            color=0xffd700
        )
        
        leaderboard_text = ""
        for i, (profile_dict, dominance_quotient) in enumerate(leaderboard_data[:limit], 1):
            # Get Discord user
            try:
                user = self.bot.get_user(int(profile_dict['discord_id']))
                display_name = user.display_name if user else profile_dict.get('discord_username', 'Unknown')
            except:
                display_name = profile_dict.get('discord_username', 'Unknown')
            
            # Medal emojis
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            win_rate = (profile_dict.get('wins', 0) / max(profile_dict.get('games_played', 1), 1)) * 100
            
            leaderboard_text += f"{medal} **{display_name}**\n"
            leaderboard_text += f"   Dominance Quotient: {dominance_quotient:.1f}%\n"
            leaderboard_text += f"   Games: {profile_dict.get('games_played', 0)} | Win Rate: {win_rate:.1f}%\n\n"
        
        embed.add_field(
            name="Top Players",
            value=leaderboard_text or "No qualifying players found",
            inline=False
        )
        
        embed.set_footer(text=f"Showing top {min(len(leaderboard_data), limit)} players | Based on advanced statistical analysis")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="blcsx_stats", description="Show detailed BLCSX player statistics")
    async def blcsx_stats(self, ctx, player: discord.Member = None):
        """Show detailed BLCSX statistics"""
        
        target_user = player if player else ctx.author
        profile = get_player_profile(target_user.id)
        
        if not profile:
            embed = discord.Embed(
                title="❌ Profile Not Found",
                description=f"{target_user.display_name} hasn't set up their profile yet!",
                color=0xff0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        # Convert profile to dict
        if hasattr(profile, '__dict__'):
            profile_dict = profile.__dict__
        else:
            profile_dict = dict(profile)
        
        # Calculate per-game stats
        games_played = max(profile_dict.get('games_played', 1), 1)
        goals_per_game = profile_dict.get('total_goals', 0) / games_played
        assists_per_game = profile_dict.get('total_assists', 0) / games_played
        saves_per_game = profile_dict.get('total_saves', 0) / games_played
        shots_per_game = profile_dict.get('total_shots', 0) / games_played
        avg_score = profile_dict.get('total_score', 0) / games_played
        
        # Calculate dominance quotient
        all_profiles = get_all_profiles()
        all_player_data = []
        
        for p in all_profiles:
            if hasattr(p, '__dict__'):
                p_dict = p.__dict__
            else:
                p_dict = dict(p)
                
            if p_dict.get('games_played', 0) > 0:
                all_player_data.append({
                    'goals_per_game': p_dict.get('total_goals', 0) / p_dict['games_played'],
                    'assists_per_game': p_dict.get('total_assists', 0) / p_dict['games_played'],
                    'saves_per_game': p_dict.get('total_saves', 0) / p_dict['games_played'],
                    'shots_per_game': p_dict.get('total_shots', 0) / p_dict['games_played'],
                    'shot_percentage': p_dict.get('goal_percentage', 0),
                    'avg_score': p_dict.get('total_score', 0) / p_dict['games_played']
                })
        
        player_data = {
            'goals_per_game': goals_per_game,
            'assists_per_game': assists_per_game,
            'saves_per_game': saves_per_game,
            'shots_per_game': shots_per_game,
            'shot_percentage': profile_dict.get('goal_percentage', 0),
            'avg_score': avg_score
        }
        
        dominance_quotient = self.calculator.calculate_dominance_quotient(player_data, all_player_data)
        
        # Create detailed stats embed
        embed = discord.Embed(
            title=f"📊 {target_user.display_name}'s BLCSX Statistics",
            color=0x4CAF50 if dominance_quotient >= 70 else 0xFFC107 if dominance_quotient >= 45 else 0xF44336
        )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Overall performance
        win_rate = (profile_dict.get('wins', 0) / games_played) * 100
        
        # Calculate rank
        all_dominance = []
        for p in all_player_data:
            dq = self.calculator.calculate_dominance_quotient(p, all_player_data)
            all_dominance.append(dq)
        rank = len([dq for dq in all_dominance if dq > dominance_quotient]) + 1
        
        embed.add_field(
            name="🏆 Overall Performance",
            value=f"**Dominance Quotient:** {dominance_quotient:.1f}%\n"
                  f"**League Rank:** #{rank} of {len(all_player_data)}\n"
                  f"**Games Played:** {profile_dict.get('games_played', 0)}\n"
                  f"**Win Rate:** {win_rate:.1f}% ({profile_dict.get('wins', 0)}W-{profile_dict.get('losses', 0)}L)",
            inline=False
        )
        
        # Per-game stats
        embed.add_field(
            name="📈 Per Game Averages",
            value=f"**Goals:** {goals_per_game:.2f}\n"
                  f"**Assists:** {assists_per_game:.2f}\n"
                  f"**Saves:** {saves_per_game:.2f}\n"
                  f"**Shots:** {shots_per_game:.2f}\n"
                  f"**Score:** {avg_score:.0f}",
            inline=True
        )
        
        # Percentages and efficiency
        embed.add_field(
            name="🎯 Efficiency Stats",
            value=f"**Goal %:** {profile_dict.get('goal_percentage', 0):.1f}%\n"
                  f"**Save %:** {profile_dict.get('save_percentage', 0):.1f}%\n"
                  f"**Win %:** {profile_dict.get('win_percentage', 0):.1f}%",
            inline=True
        )
        
        # Career totals
        embed.add_field(
            name="🏆 Career Totals",
            value=f"**Goals:** {profile_dict.get('total_goals', 0):,}\n"
                  f"**Assists:** {profile_dict.get('total_assists', 0):,}\n"
                  f"**Saves:** {profile_dict.get('total_saves', 0):,}\n"
                  f"**Score:** {profile_dict.get('total_score', 0):,}",
            inline=True
        )
        
        # Additional info
        embed.set_footer(text=f"BLCSX Statistics • Last updated: {profile_dict.get('last_updated', 'Unknown')}")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="analyze_league", description="[Admin] Analyze league winning patterns and update weights")
    @commands.has_permissions(administrator=True)
    async def analyze_league(self, ctx):
        """Admin command to reanalyze winning patterns"""
        
        await ctx.response.defer()
        
        try:
            profiles = get_all_profiles()
            
            if len(profiles) < 5:
                embed = discord.Embed(
                    title="⚠️ Insufficient Data",
                    description="Need at least 5 players with game data to perform analysis.",
                    color=0xff9900
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Convert profiles for analysis
            all_player_data = []
            for profile in profiles:
                if hasattr(profile, '__dict__'):
                    profile_dict = profile.__dict__
                else:
                    profile_dict = dict(profile)
                
                if profile_dict.get('games_played', 0) >= 3:  # Minimum 3 games
                    games_played = profile_dict['games_played']
                    player_data = {
                        'goals_per_game': profile_dict.get('total_goals', 0) / games_played,
                        'assists_per_game': profile_dict.get('total_assists', 0) / games_played,
                        'saves_per_game': profile_dict.get('total_saves', 0) / games_played,
                        'shots_per_game': profile_dict.get('total_shots', 0) / games_played,
                        'shot_percentage': profile_dict.get('goal_percentage', 0),
                        'avg_score': profile_dict.get('total_score', 0) / games_played,
                        'games_played': profile_dict.get('games_played', 0),
                        'wins': profile_dict.get('wins', 0)
                    }
                    all_player_data.append(player_data)
            
            # Analyze winning patterns
            old_weights = self.calculator.stat_weights.copy()
            new_weights = self.calculator.analyze_winning_patterns(all_player_data)
            
            # Create analysis embed
            embed = discord.Embed(
                title="📊 League Analysis Complete",
                description=f"Analyzed {len(all_player_data)} players with 3+ games",
                color=0x00ff00
            )
            
            # Show weight changes
            weight_changes = ""
            for stat, new_weight in new_weights.items():
                old_weight = old_weights.get(stat, 0)
                change = new_weight - old_weight
                emoji = "📈" if change > 0.02 else "📉" if change < -0.02 else "➖"
                weight_changes += f"{emoji} **{stat.replace('_', ' ').title()}:** {new_weight:.1%} ({change:+.1%})\n"
            
            embed.add_field(
                name="🎯 Updated Stat Weights",
                value=weight_changes,
                inline=False
            )
            
            embed.add_field(
                name="💡 Analysis Insights",
                value="• Weights show which stats correlate most with winning\n"
                      "• Higher weights = more important for team success\n"
                      "• Dominance quotients will be recalculated accordingly",
                inline=False
            )
            
            embed.set_footer(text="All player dominance quotients have been updated with new weights")
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in league analysis: {e}")
            embed = discord.Embed(
                title="❌ Analysis Failed",
                description=f"Error during analysis: {str(e)}",
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="player_comparison", description="Compare two players side-by-side")
    async def player_comparison(self, ctx, player1: discord.Member, player2: discord.Member):
        """Compare two players statistically"""
        
        # Get both profiles
        profile1 = get_player_profile(player1.id)
        profile2 = get_player_profile(player2.id)
        
        if not profile1 or not profile2:
            missing = []
            if not profile1:
                missing.append(player1.display_name)
            if not profile2:
                missing.append(player2.display_name)
            
            embed = discord.Embed(
                title="❌ Profile(s) Not Found",
                description=f"Missing profiles for: {', '.join(missing)}",
                color=0xff0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        # Convert to dicts
        if hasattr(profile1, '__dict__'):
            p1_dict = profile1.__dict__
        else:
            p1_dict = dict(profile1)
            
        if hasattr(profile2, '__dict__'):
            p2_dict = profile2.__dict__
        else:
            p2_dict = dict(profile2)
        
        # Calculate per-game stats for both
        games1 = max(p1_dict.get('games_played', 1), 1)
        games2 = max(p2_dict.get('games_played', 1), 1)
        
        p1_stats = {
            'goals_per_game': p1_dict.get('total_goals', 0) / games1,
            'assists_per_game': p1_dict.get('total_assists', 0) / games1,
            'saves_per_game': p1_dict.get('total_saves', 0) / games1,
            'shots_per_game': p1_dict.get('total_shots', 0) / games1,
            'shot_percentage': p1_dict.get('goal_percentage', 0),
            'avg_score': p1_dict.get('total_score', 0) / games1,
            'win_percentage': p1_dict.get('win_percentage', 0)
        }
        
        p2_stats = {
            'goals_per_game': p2_dict.get('total_goals', 0) / games2,
            'assists_per_game': p2_dict.get('total_assists', 0) / games2,
            'saves_per_game': p2_dict.get('total_saves', 0) / games2,
            'shots_per_game': p2_dict.get('total_shots', 0) / games2,
            'shot_percentage': p2_dict.get('goal_percentage', 0),
            'avg_score': p2_dict.get('total_score', 0) / games2,
            'win_percentage': p2_dict.get('win_percentage', 0)
        }
        
        # Calculate dominance quotients
        all_profiles = get_all_profiles()
        all_player_data = []
        for p in all_profiles:
            if hasattr(p, '__dict__'):
                p_dict = p.__dict__
            else:
                p_dict = dict(p)
            
            if p_dict.get('games_played', 0) > 0:
                all_player_data.append({
                    'goals_per_game': p_dict.get('total_goals', 0) / p_dict['games_played'],
                    'assists_per_game': p_dict.get('total_assists', 0) / p_dict['games_played'],
                    'saves_per_game': p_dict.get('total_saves', 0) / p_dict['games_played'],
                    'shots_per_game': p_dict.get('total_shots', 0) / p_dict['games_played'],
                    'shot_percentage': p_dict.get('goal_percentage', 0),
                    'avg_score': p_dict.get('total_score', 0) / p_dict['games_played']
                })
        
        dq1 = self.calculator.calculate_dominance_quotient(p1_stats, all_player_data)
        dq2 = self.calculator.calculate_dominance_quotient(p2_stats, all_player_data)
        
        # Create comparison embed
        embed = discord.Embed(
            title=f"⚔️ Player Comparison",
            description=f"**{player1.display_name}** vs **{player2.display_name}**",
            color=0x0099ff
        )
        
        # Dominance quotient comparison
        dq_winner = "🏆" if dq1 > dq2 else ""
        dq_winner2 = "🏆" if dq2 > dq1 else ""
        if abs(dq1 - dq2) < 1:
            dq_winner = dq_winner2 = "🤝"  # Tie
        
        embed.add_field(
            name="🎯 Dominance Quotient",
            value=f"{dq_winner} **{player1.display_name}:** {dq1:.1f}%\n"
                  f"{dq_winner2} **{player2.display_name}:** {dq2:.1f}%",
            inline=False
        )
        
        # Statistical comparison
        stats_comparison = ""
        stat_labels = {
            'goals_per_game': 'Goals/Game',
            'assists_per_game': 'Assists/Game', 
            'saves_per_game': 'Saves/Game',
            'shots_per_game': 'Shots/Game',
            'shot_percentage': 'Shot %',
            'avg_score': 'Avg Score',
            'win_percentage': 'Win %'
        }
        
        for stat, label in stat_labels.items():
            val1 = p1_stats.get(stat, 0)
            val2 = p2_stats.get(stat, 0)
            
            if stat in ['shot_percentage', 'win_percentage']:
                winner1 = "🟢" if val1 > val2 else "🔴" if val1 < val2 else "🟡"
                winner2 = "🟢" if val2 > val1 else "🔴" if val2 < val1 else "🟡"
                stats_comparison += f"**{label}:** {winner1} {val1:.1f}% vs {winner2} {val2:.1f}%\n"
            else:
                winner1 = "🟢" if val1 > val2 else "🔴" if val1 < val2 else "🟡"
                winner2 = "🟢" if val2 > val1 else "🔴" if val2 < val1 else "🟡"
                stats_comparison += f"**{label}:** {winner1} {val1:.2f} vs {winner2} {val2:.2f}\n"
        
        embed.add_field(
            name="📊 Head-to-Head Stats",
            value=stats_comparison,
            inline=False
        )
        
        # Games played comparison
        embed.add_field(
            name="🎮 Experience",
            value=f"**{player1.display_name}:** {p1_dict.get('games_played', 0)} games\n"
                  f"**{player2.display_name}:** {p2_dict.get('games_played', 0)} games",
            inline=True
        )
        
        # Overall verdict
        p1_wins = sum(1 for stat in stat_labels.keys() if p1_stats.get(stat, 0) > p2_stats.get(stat, 0))
        p2_wins = sum(1 for stat in stat_labels.keys() if p2_stats.get(stat, 0) > p1_stats.get(stat, 0))
        
        if p1_wins > p2_wins:
            verdict = f"🏆 **{player1.display_name}** leads in {p1_wins}/{len(stat_labels)} categories"
        elif p2_wins > p1_wins:
            verdict = f"🏆 **{player2.display_name}** leads in {p2_wins}/{len(stat_labels)} categories"
        else:
            verdict = "🤝 **Evenly Matched** - Close competition!"
        
        embed.add_field(
            name="🏁 Verdict",
            value=verdict,
            inline=False
        )
        
        embed.set_footer(text="🟢 = Better • 🔴 = Worse • 🟡 = Equal")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="top_performers", description="Show top performers in specific categories")
    async def top_performers(self, ctx, 
                           category: str = discord.Option(
                               description="Choose a category",
                               choices=[
                                   discord.OptionChoice(name="Goals per Game", value="goals"),
                                   discord.OptionChoice(name="Assists per Game", value="assists"),
                                   discord.OptionChoice(name="Saves per Game", value="saves"),
                                   discord.OptionChoice(name="Shot Percentage", value="shooting"),
                                   discord.OptionChoice(name="Average Score", value="score"),
                                   discord.OptionChoice(name="Win Percentage", value="wins"),
                                   discord.OptionChoice(name="Most Consistent", value="consistency")
                               ]
                           ),
                           limit: int = 5):
        """Show top performers in specific statistical categories"""
        
        profiles = get_all_profiles()
        
        if not profiles:
            await ctx.respond("❌ No profiles found in the database.", ephemeral=True)
            return
        
        # Filter profiles with enough games
        min_games = 3
        qualified_profiles = []
        
        for profile in profiles:
            if hasattr(profile, '__dict__'):
                profile_dict = profile.__dict__
            else:
                profile_dict = dict(profile)
            
            if profile_dict.get('games_played', 0) >= min_games:
                qualified_profiles.append(profile_dict)
        
        if not qualified_profiles:
            embed = discord.Embed(
                title="❌ No Qualified Players",
                description=f"No players found with at least {min_games} games played.",
                color=0xff0000
            )
            await ctx.respond(embed=embed)
            return
        
        # Calculate and sort based on category
        category_data = []
        
        for profile_dict in qualified_profiles:
            games_played = profile_dict['games_played']
            
            if category == "goals":
                value = profile_dict.get('total_goals', 0) / games_played
                category_name = "Goals per Game"
                format_str = "{:.2f}"
            elif category == "assists":
                value = profile_dict.get('total_assists', 0) / games_played
                category_name = "Assists per Game" 
                format_str = "{:.2f}"
            elif category == "saves":
                value = profile_dict.get('total_saves', 0) / games_played
                category_name = "Saves per Game"
                format_str = "{:.2f}"
            elif category == "shooting":
                value = profile_dict.get('goal_percentage', 0)
                category_name = "Shot Percentage"
                format_str = "{:.1f}%"
            elif category == "score":
                value = profile_dict.get('total_score', 0) / games_played
                category_name = "Average Score"
                format_str = "{:.0f}"
            elif category == "wins":
                value = profile_dict.get('win_percentage', 0)
                category_name = "Win Percentage"
                format_str = "{:.1f}%"
            elif category == "consistency":
                # Consistency = win percentage (simplified for demo)
                value = profile_dict.get('win_percentage', 0)
                category_name = "Most Consistent (Win %)"
                format_str = "{:.1f}%"
            
            category_data.append((profile_dict, value, format_str))
        
        # Sort by value (descending)
        category_data.sort(key=lambda x: x[1], reverse=True)
        
        # Create embed
        embed = discord.Embed(
            title=f"🏆 Top {category_name} Leaders",
            color=0xffd700
        )
        
        leaderboard_text = ""
        for i, (profile_dict, value, format_str) in enumerate(category_data[:limit], 1):
            # Get Discord user
            try:
                user = self.bot.get_user(int(profile_dict['discord_id']))
                display_name = user.display_name if user else profile_dict.get('discord_username', 'Unknown')
            except:
                display_name = profile_dict.get('discord_username', 'Unknown')
            
            # Medal emojis
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            leaderboard_text += f"{medal} **{display_name}**\n"
            leaderboard_text += f"   {category_name}: {format_str.format(value)}\n"
            leaderboard_text += f"   Games Played: {profile_dict.get('games_played', 0)}\n\n"
        
        embed.add_field(
            name=f"Top Performers",
            value=leaderboard_text,
            inline=False
        )
        
        embed.set_footer(text=f"Minimum {min_games} games required • Showing top {min(len(category_data), limit)} players")
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(BLCSXProfilesCog(bot))