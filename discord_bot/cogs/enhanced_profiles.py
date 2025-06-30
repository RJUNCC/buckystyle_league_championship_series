# File: discord_bot/cogs/enhanced_profiles.py

import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance
import matplotlib.pyplot as plt
import io
from typing import Dict, List, Optional, Tuple
import math
from datetime import datetime
import logging
import random
from models.player_profile import (
    get_player_profile, create_or_update_profile, 
    get_all_profiles, update_player_stats
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CreativeProfileCardGenerator:
    def __init__(self):
        # Card dimensions
        self.card_width = 1200
        self.card_height = 900
        
        # Enhanced color schemes - multiple themes
        self.color_themes = {
            'classic': {
                'elite': '#4CAF50', 'above_avg': '#8BC34A', 'average': '#FFC107',
                'below_avg': '#FF9800', 'replacement': '#F44336', 'background': '#FFFFFF',
                'header': '#1565C0', 'text': '#2E2E2E', 'accent': '#E3F2FD'
            },
            'neon': {
                'elite': '#00FF41', 'above_avg': '#39FF14', 'average': '#FFFF00',
                'below_avg': '#FF8C00', 'replacement': '#FF1744', 'background': '#0D1117',
                'header': '#7C3AED', 'text': '#FFFFFF', 'accent': '#1F2937'
            },
            'cyberpunk': {
                'elite': '#00FFFF', 'above_avg': '#00C9FF', 'average': '#FFB800',
                'below_avg': '#FF6B35', 'replacement': '#FF073A', 'background': '#0F0F23',
                'header': '#FF00FF', 'text': '#FFFFFF', 'accent': '#2D1B69'
            },
            'retro': {
                'elite': '#FF6B9D', 'above_avg': '#C44569', 'average': '#F8B500',
                'below_avg': '#FF7675', 'replacement': '#74B9FF', 'background': '#2D3436',
                'header': '#A29BFE', 'text': '#FFFFFF', 'accent': '#636E72'
            },
            'ocean': {
                'elite': '#00B894', 'above_avg': '#00CEC9', 'average': '#FDCB6E',
                'below_avg': '#E17055', 'replacement': '#D63031', 'background': '#74B9FF',
                'header': '#0984E3', 'text': '#FFFFFF', 'accent': '#DDD6FE'
            }
        }
        
        # Dynamic rank names based on performance
        self.rank_names = {
            'elite': ['Grand Master', 'Champion', 'Elite', 'Superstar', 'Legend'],
            'above_avg': ['Expert', 'Advanced', 'Skilled', 'Veteran', 'Pro'],
            'average': ['Competent', 'Solid', 'Reliable', 'Steady', 'Balanced'],
            'below_avg': ['Developing', 'Learning', 'Improving', 'Rising', 'Growing'],
            'replacement': ['Rookie', 'Prospect', 'Trainee', 'Newcomer', 'Fresh']
        }
    
    def get_theme_for_performance(self, dominance_quotient: float) -> str:
        """Select theme based on performance"""
        if dominance_quotient >= 80:
            return random.choice(['cyberpunk', 'neon'])
        elif dominance_quotient >= 65:
            return 'ocean'
        elif dominance_quotient >= 45:
            return 'classic'
        elif dominance_quotient >= 25:
            return 'retro'
        else:
            return random.choice(['classic', 'retro'])
    
    def get_dynamic_rank(self, dominance_quotient: float) -> str:
        """Get dynamic rank name based on performance"""
        if dominance_quotient >= 80:
            return random.choice(self.rank_names['elite'])
        elif dominance_quotient >= 65:
            return random.choice(self.rank_names['above_avg'])
        elif dominance_quotient >= 45:
            return random.choice(self.rank_names['average'])
        elif dominance_quotient >= 25:
            return random.choice(self.rank_names['below_avg'])
        else:
            return random.choice(self.rank_names['replacement'])
    
    def get_font(self, size: int, bold: bool = False):
        """Get font with enhanced fallback system"""
        font_paths = [
            # Windows fonts
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            # macOS fonts
            "/System/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            # Linux fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # Basic fallbacks
            "arial.ttf", "Arial.ttf"
        ]
        
        for font_path in font_paths:
            try:
                if bold:
                    return ImageFont.truetype(font_path, size)
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        return ImageFont.load_default()
    
    def get_stat_color(self, percentile: float, theme: str) -> str:
        """Get color based on percentile and theme"""
        colors = self.color_themes[theme]
        if percentile >= 80:
            return colors['elite']
        elif percentile >= 65:
            return colors['above_avg']
        elif percentile >= 45:
            return colors['average']
        elif percentile >= 25:
            return colors['below_avg']
        else:
            return colors['replacement']
    
    def calculate_percentile(self, value: float, all_values: List[float]) -> float:
        """Calculate percentile"""
        if not all_values or len(all_values) <= 1:
            return 50.0
        return (sum(1 for v in all_values if v < value) / len(all_values)) * 100
    
    async def download_discord_avatar(self, user: discord.User) -> Image.Image:
        """Download and enhance Discord avatar with creative effects"""
        try:
            avatar_url = user.display_avatar.url
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as response:
                    if response.status == 200:
                        avatar_data = await response.read()
                        avatar_img = Image.open(io.BytesIO(avatar_data))
                        
                        # Convert to RGB
                        if avatar_img.mode != 'RGB':
                            avatar_img = avatar_img.convert('RGB')
                        
                        # Enhanced processing
                        avatar_img = avatar_img.resize((240, 240), Image.Resampling.LANCZOS)
                        
                        # Apply subtle enhancement
                        enhancer = ImageEnhance.Sharpness(avatar_img)
                        avatar_img = enhancer.enhance(1.2)
                        
                        enhancer = ImageEnhance.Contrast(avatar_img)
                        avatar_img = enhancer.enhance(1.1)
                        
                        # Create circular mask with border
                        mask = Image.new('L', (240, 240), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((5, 5, 235, 235), fill=255)
                        
                        # Apply mask
                        output = ImageOps.fit(avatar_img, mask.size, centering=(0.5, 0.5))
                        output.putalpha(mask)
                        
                        return output
        except Exception as e:
            logger.error(f"Failed to download avatar: {e}")
        
        # Enhanced default avatar
        avatar = Image.new('RGBA', (240, 240), (0, 0, 0, 0))
        draw = ImageDraw.Draw(avatar)
        
        # Gradient background
        for i in range(240):
            color_intensity = int(100 + (i / 240) * 100)
            draw.ellipse((i//4, i//4, 240-i//4, 240-i//4), 
                        fill=(color_intensity, color_intensity//2, 255-color_intensity))
        
        draw.text((120, 120), "RL", fill='white', anchor='mm', font=self.get_font(48, True))
        return avatar
    
    def create_enhanced_radar_chart(self, radar_stats: List[float], theme: str) -> Image.Image:
        """Create enhanced radar chart with theme colors and effects"""
        # Create figure with dark/light theme support
        theme_colors = self.color_themes[theme]
        bg_color = theme_colors['background']
        text_color = theme_colors['text']
        
        plt.style.use('dark_background' if bg_color == '#0D1117' else 'default')
        
        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(projection='polar'))
        fig.patch.set_facecolor(bg_color)
        
        # Enhanced categories
        categories = ['Score', 'Goals', 'Assists', 'Saves', 'Shots', 'Accuracy']
        N = len(categories)
        
        # Calculate angles
        angles = [90 - (360/N * i) for i in range(N)]
        angles_rad = [math.radians(angle) for angle in angles]
        angles_rad += angles_rad[:1]
        
        values = radar_stats + radar_stats[:1]
        
        # Enhanced plotting with gradient effect
        ax.plot(angles_rad, values, 'o-', linewidth=4, 
               color=theme_colors['elite'], markersize=10, 
               markerfacecolor=theme_colors['elite'], 
               markeredgecolor='white', markeredgewidth=2)
        
        # Multiple fill layers for depth
        ax.fill(angles_rad, values, alpha=0.3, color=theme_colors['elite'])
        ax.fill(angles_rad, values, alpha=0.1, color=theme_colors['above_avg'])
        
        # Enhanced grid
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], 
                          fontsize=10, color=text_color, alpha=0.7)
        ax.grid(True, alpha=0.3, color=text_color)
        
        # Custom category labels with better positioning
        for angle, category in zip(angles_rad[:-1], categories):
            x = 115 * math.cos(angle)
            y = 115 * math.sin(angle)
            
            ha = 'center'
            va = 'center'
            if x > 30: ha = 'left'
            elif x < -30: ha = 'right'
            if y > 30: va = 'bottom'
            elif y < -30: va = 'top'
            
            ax.text(angle, 115, category, ha=ha, va=va, fontsize=12, 
                   fontweight='bold', color=text_color)
        
        # Remove radial labels and spines for cleaner look
        ax.set_rlabel_position(0)
        ax.spines['polar'].set_visible(False)
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', 
                   facecolor=bg_color, edgecolor='none', pad_inches=0.1)
        buffer.seek(0)
        plt.close()
        
        radar_img = Image.open(buffer)
        return radar_img.resize((420, 420))
    
    def add_creative_effects(self, img: Image.Image, theme: str) -> Image.Image:
        """Add creative visual effects based on theme"""
        draw = ImageDraw.Draw(img)
        theme_colors = self.color_themes[theme]
        
        if theme in ['neon', 'cyberpunk']:
            # Add neon glow effects
            for i in range(3):
                # Glowing borders
                border_color = (*ImageColor.getrgb(theme_colors['header']), 50)
                draw.rectangle([i, i, self.card_width-i, self.card_height-i], 
                             outline=border_color, width=2)
            
            # Scan lines effect
            for y in range(0, self.card_height, 4):
                draw.line([(0, y), (self.card_width, y)], 
                         fill=(*ImageColor.getrgb(theme_colors['accent']), 10), width=1)
        
        elif theme == 'retro':
            # Add retro grid pattern
            grid_color = (*ImageColor.getrgb(theme_colors['accent']), 30)
            for x in range(0, self.card_width, 50):
                draw.line([(x, 0), (x, self.card_height)], fill=grid_color, width=1)
            for y in range(0, self.card_height, 50):
                draw.line([(0, y), (self.card_width, y)], fill=grid_color, width=1)
        
        return img
    
    async def generate_creative_profile_card(self, user: discord.User, profile: Dict, 
                                          all_profiles: List[Dict], guild: discord.Guild = None) -> io.BytesIO:
        """Generate creative profile card with dynamic theming and effects"""
        
        # Calculate dominance quotient first to determine theme
        games_played = max(profile.get('games_played', 1), 1)
        player_data = {
            'goals_per_game': profile.get('total_goals', 0) / games_played,
            'assists_per_game': profile.get('total_assists', 0) / games_played,
            'saves_per_game': profile.get('total_saves', 0) / games_played,
            'shots_per_game': profile.get('total_shots', 0) / games_played,
            'shot_percentage': profile.get('goal_percentage', 0),
            'avg_score': profile.get('total_score', 0) / games_played,
        }
        
        # Mock dominance quotient calculation for theming
        dominance_quotient = min(100, max(0, 
            (player_data['avg_score'] / 500 * 30) +
            (player_data['goals_per_game'] * 15) +
            (player_data['assists_per_game'] * 10) +
            (player_data['saves_per_game'] * 15) +
            (player_data['shot_percentage'] / 100 * 30)
        ))
        
        # Select theme based on performance
        theme = self.get_theme_for_performance(dominance_quotient)
        theme_colors = self.color_themes[theme]
        
        # Create base image with theme background
        img = Image.new('RGB', (self.card_width, self.card_height), theme_colors['background'])
        draw = ImageDraw.Draw(img)
        
        # Add creative background effects
        img = self.add_creative_effects(img, theme)
        
        # Enhanced fonts
        title_font = self.get_font(36, True)
        large_stat_font = self.get_font(56, True)
        medium_font = self.get_font(28, True)
        stat_font = self.get_font(22, True)
        label_font = self.get_font(16)
        small_font = self.get_font(14)
        
        # === HEADER SECTION WITH DYNAMIC BRANDING ===
        header_height = 90
        draw.rectangle([0, 0, self.card_width, header_height], fill=theme_colors['header'])
        
        # Enhanced header with gradient effect
        for i in range(header_height):
            alpha = int(255 * (1 - i / header_height * 0.3))
            overlay_color = (*ImageColor.getrgb(theme_colors['accent']), alpha)
            draw.line([(0, i), (self.card_width, i)], fill=overlay_color, width=1)
        
        # Dynamic rank badge
        rank_name = self.get_dynamic_rank(dominance_quotient)
        draw.text((30, 25), f"{rank_name}", font=medium_font, fill='white')
        draw.text((30, 55), f"BLCSX {theme.title()} Series", font=label_font, fill='white')
        
        # Player name with outline effect
        name_x = 300
        # Outline
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((name_x + dx, 45 + dy), user.display_name, 
                             font=title_font, fill='black')
        # Main text
        draw.text((name_x, 45), user.display_name, font=title_font, fill='white')
        
        # Server icon with enhanced styling
        try:
            if guild and guild.icon:
                server_icon_url = guild.icon.url
                async with aiohttp.ClientSession() as session:
                    async with session.get(server_icon_url) as response:
                        if response.status == 200:
                            server_icon_data = await response.read()
                            server_icon = Image.open(io.BytesIO(server_icon_data))
                            server_icon = server_icon.resize((70, 70))
                            # Add border
                            bordered_icon = Image.new('RGBA', (74, 74), 'white')
                            bordered_icon.paste(server_icon, (2, 2))
                            img.paste(bordered_icon, (self.card_width - 85, 10))
        except:
            # Enhanced fallback
            draw.ellipse([self.card_width - 85, 10, self.card_width - 15, 80], 
                        fill=theme_colors['elite'])
            draw.text((self.card_width - 50, 45), "BLCSX", 
                     font=small_font, fill='white', anchor='mm')
        
        # === ENHANCED PLAYER SECTION ===
        # Large avatar with effects
        large_avatar = await self.download_discord_avatar(user)
        if large_avatar.mode == 'RGBA':
            avatar_bg = Image.new('RGB', (240, 240), theme_colors['background'])
            avatar_bg.paste(large_avatar, (0, 0), large_avatar)
            large_avatar = avatar_bg
        
        # Add avatar border effect
        avatar_border = Image.new('RGB', (250, 250), theme_colors['elite'])
        draw_border = ImageDraw.Draw(avatar_border)
        draw_border.ellipse([5, 5, 245, 245], fill=theme_colors['background'])
        avatar_border.paste(large_avatar, (5, 5))
        img.paste(avatar_border, (30, 120))
        
        # === MAIN STAT WITH ENHANCED STYLING ===
        main_box_x = 320
        main_box_y = 140
        main_box_width = 300
        main_box_height = 140
        
        # Gradient background for main stat
        main_color = self.get_stat_color(dominance_quotient, theme)
        
        # Create gradient effect
        for i in range(main_box_height):
            alpha = 1 - (i / main_box_height * 0.3)
            gradient_color = ImageColor.getrgb(main_color)
            gradient_color = tuple(int(c * alpha) for c in gradient_color)
            draw.rectangle([main_box_x, main_box_y + i, main_box_x + main_box_width, main_box_y + i + 1], 
                          fill=gradient_color)
        
        # Enhanced main stat text with shadow
        # Shadow
        draw.text((main_box_x + main_box_width//2 + 3, main_box_y + main_box_height//2 + 3), 
                 f"{dominance_quotient:.0f}%", 
                 font=large_stat_font, fill='black', anchor='mm')
        # Main text
        draw.text((main_box_x + main_box_width//2, main_box_y + main_box_height//2), 
                 f"{dominance_quotient:.0f}%", 
                 font=large_stat_font, fill='white', anchor='mm')
        
        # Enhanced label with background
        label_bg_y = main_box_y + main_box_height + 10
        draw.rectangle([main_box_x, label_bg_y, main_box_x + 200, label_bg_y + 25], 
                      fill=theme_colors['accent'])
        draw.text((main_box_x + 5, label_bg_y + 12), "Dominance Quotient", 
                 font=label_font, fill=theme_colors['text'], anchor='lm')
        
        # === ENHANCED STATS GRID ===
        stats_y = 320
        draw.text((30, stats_y), "Performance Metrics", font=medium_font, fill=theme_colors['text'])
        
        # Calculate all percentiles
        all_player_data = []
        for p in all_profiles:
            if p.get('games_played', 0) > 0:
                all_player_data.append({
                    'avg_score': p.get('total_score', 0) / p['games_played'],
                    'goals_per_game': p.get('total_goals', 0) / p['games_played'],
                    'assists_per_game': p.get('total_assists', 0) / p['games_played'],
                    'saves_per_game': p.get('total_saves', 0) / p['games_played'],
                    'shots_per_game': p.get('total_shots', 0) / p['games_played'],
                    'shot_percentage': p.get('goal_percentage', 0),
                })
        
        # Enhanced stats layout
        stat_box_width = 160
        stat_box_height = 90
        stat_spacing = 25
        first_row_y = stats_y + 50
        
        all_stats = [
            ("Average Score", player_data['avg_score'], 'avg_score'),
            ("Goals/Game", player_data['goals_per_game'], 'goals_per_game'),
            ("Assists/Game", player_data['assists_per_game'], 'assists_per_game'),
            ("Saves/Game", player_data['saves_per_game'], 'saves_per_game'),
            ("Shots/Game", player_data['shots_per_game'], 'shots_per_game'),
            ("Shot Accuracy", player_data['shot_percentage'], 'shot_percentage')
        ]
        
        for i, (label, value, stat_key) in enumerate(all_stats):
            row = i // 3
            col = i % 3
            x = 30 + col * (stat_box_width + stat_spacing)
            y = first_row_y + row * (stat_box_height + 40)
            
            # Calculate percentile
            if all_player_data:
                all_values = [p.get(stat_key, 0) for p in all_player_data]
                percentile = self.calculate_percentile(value, all_values)
            else:
                percentile = 50
            
            color = self.get_stat_color(percentile, theme)
            
            # Enhanced stat box with 3D effect
            # Shadow
            draw.rectangle([x + 3, y + 3, x + stat_box_width + 3, y + stat_box_height + 3], 
                          fill='black')
            # Main box
            draw.rectangle([x, y, x + stat_box_width, y + stat_box_height], fill=color)
            
            # Highlight
            draw.rectangle([x, y, x + stat_box_width, y + 20], 
                          fill=(*ImageColor.getrgb(color), 100))
            
            # Value with better formatting
            if stat_key == 'shot_percentage':
                value_text = f"{value:.1f}%"
            else:
                value_text = f"{value:.1f}"
            
            # Shadow text
            draw.text((x + stat_box_width//2 + 1, y + stat_box_height//2 + 1), 
                     value_text, font=stat_font, fill='black', anchor='mm')
            # Main text
            draw.text((x + stat_box_width//2, y + stat_box_height//2), 
                     value_text, font=stat_font, fill='white', anchor='mm')
            
            # Enhanced label with background
            draw.rectangle([x, y + stat_box_height + 5, x + stat_box_width, y + stat_box_height + 25], 
                          fill=theme_colors['accent'])
            draw.text((x + stat_box_width//2, y + stat_box_height + 15), label, 
                     font=small_font, fill=theme_colors['text'], anchor='mm')
        
        # === ENHANCED RADAR CHART ===
        radar_x = 670
        radar_y = 120
        
        # Title with enhanced styling
        draw.text((radar_x + 210, radar_y - 30), "Skill Analysis", 
                 font=medium_font, fill=theme_colors['text'], anchor='mm')
        
        # Generate radar data
        radar_values = []
        for stat_key in ['avg_score', 'goals_per_game', 'assists_per_game', 
                        'saves_per_game', 'shots_per_game', 'shot_percentage']:
            if all_player_data:
                all_values = [p.get(stat_key, 0) for p in all_player_data]
                percentile = self.calculate_percentile(player_data.get(stat_key, 0), all_values)
            else:
                percentile = 50
            radar_values.append(min(100, max(0, percentile)))
        
        # Create and paste enhanced radar chart
        radar_chart = self.create_enhanced_radar_chart(radar_values, theme)
        img.paste(radar_chart, (radar_x, radar_y))
        
        # === ENHANCED LEGEND ===
        legend_y = self.card_height - 90
        legend_start_x = 30
        
        # Title
        draw.text((legend_start_x, legend_y - 25), "Performance Levels", 
                 font=label_font, fill=theme_colors['text'])
        
        legend_items = [
            ("Elite", theme_colors['elite']),
            ("Above Average", theme_colors['above_avg']),
            ("Average", theme_colors['average']),
            ("Below Average", theme_colors['below_avg']),
            ("Replacement", theme_colors['replacement'])
        ]
        
        legend_spacing = 200
        for i, (label, color) in enumerate(legend_items):
            x = legend_start_x + i * legend_spacing
            
            # Enhanced legend box with border
            draw.rectangle([x - 1, legend_y - 1, x + 21, legend_y + 21], fill='white')
            draw.rectangle([x, legend_y, x + 20, legend_y + 20], fill=color)
            
            draw.text((x + 25, legend_y + 10), label, 
                     font=small_font, fill=theme_colors['text'], anchor='lm')
        
        # Enhanced footer
        draw.text((30, self.card_height - 40), 
                 f"Generated on {datetime.now().strftime('%B %d, %Y')} • Theme: {theme.title()}", 
                 font=small_font, fill=theme_colors['text'])
        
        # Performance badge
        if dominance_quotient >= 80:
            badge_text = "🏆 ELITE PERFORMER"
        elif dominance_quotient >= 65:
            badge_text = "⭐ ABOVE AVERAGE"
        elif dominance_quotient >= 45:
            badge_text = "📈 SOLID PLAYER"
        else:
            badge_text = "🎯 DEVELOPING"
        
        draw.text((self.card_width - 30, self.card_height - 40), badge_text, 
                 font=small_font, fill=theme_colors['text'], anchor='rm')
        
        # Save with high quality
        buffer = io.BytesIO()
        img.save(buffer, format='PNG', quality=95, optimize=True)
        buffer.seek(0)
        
        return buffer

class EnhancedProfilesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profile_generator = CreativeProfileCardGenerator()

    @discord.slash_command(name="creative_profile", description="Generate a creative themed profile card")
    async def creative_profile(self, ctx, player: discord.Member = None, 
                              theme: str = discord.Option(
                                  description="Choose a theme (leave empty for auto)",
                                  choices=["auto", "classic", "neon", "cyberpunk", "retro", "ocean"],
                                  default="auto"
                              )):
        """Generate creative profile card with dynamic theming"""
        
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
            
            # Override theme if specified
            if theme != "auto":
                self.profile_generator.color_themes['forced'] = self.profile_generator.color_themes[theme]
                original_get_theme = self.profile_generator.get_theme_for_performance
                self.profile_generator.get_theme_for_performance = lambda x: 'forced'
            
            # Generate creative profile card
            card_buffer = await self.profile_generator.generate_creative_profile_card(
                target_user, profile_dict, all_profiles_dicts, ctx.guild
            )
            
            # Restore original theme selection if it was overridden
            if theme != "auto":
                self.profile_generator.get_theme_for_performance = original_get_theme
                del self.profile_generator.color_themes['forced']
            
            # Create embed
            embed = discord.Embed(
                title=f"🎨 {target_user.display_name}'s Creative Profile",
                description=f"**Theme:** {theme.title() if theme != 'auto' else 'Performance-Based'}\n"
                           f"**Enhanced Design:** Dynamic colors, effects, and styling",
                color=0x9b59b6
            )
            
            embed.set_footer(text="🎨 Creative Profile • Multiple themes and visual effects")
            
            # Send card
            file = discord.File(card_buffer, filename=f"{target_user.display_name}_creative_profile.png")
            await ctx.followup.send(embed=embed, file=file)
            
        except Exception as e:
            logger.error(f"Error generating creative profile: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to generate creative profile card. Please try again.",
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="profile_themes", description="Show all available creative themes")
    async def profile_themes(self, ctx):
        """Display all available themes with previews"""
        
        embed = discord.Embed(
            title="🎨 Creative Profile Themes",
            description="Choose from multiple visual themes for your profile cards!",
            color=0x9b59b6
        )
        
        theme_descriptions = {
            'auto': 'Performance-based theme selection',
            'classic': 'Clean, professional design with blue accents',
            'neon': 'Bright, electric colors with glow effects',
            'cyberpunk': 'Futuristic dark theme with cyan and magenta',
            'retro': 'Nostalgic 80s style with pastels and grid patterns',
            'ocean': 'Cool blues and teals with wave-like effects'
        }
        
        performance_themes = {
            'Elite (80%+)': 'Cyberpunk or Neon themes',
            'Above Average (65%+)': 'Ocean theme',
            'Average (45%+)': 'Classic theme',
            'Below Average (25%+)': 'Retro theme',
            'Developing (<25%)': 'Classic or Retro themes'
        }
        
        themes_text = ""
        for theme, description in theme_descriptions.items():
            themes_text += f"**{theme.title()}:** {description}\n"
        
        embed.add_field(
            name="🎯 Available Themes",
            value=themes_text,
            inline=False
        )
        
        performance_text = ""
        for level, theme in performance_themes.items():
            performance_text += f"**{level}:** {theme}\n"
        
        embed.add_field(
            name="🏆 Auto Theme Selection",
            value=performance_text,
            inline=False
        )
        
        embed.add_field(
            name="💡 Usage",
            value="• `/creative_profile` - Auto theme based on performance\n"
                  "• `/creative_profile theme:neon` - Force specific theme\n"
                  "• `/creative_profile @player theme:cyberpunk` - View others with theme",
            inline=False
        )
        
        embed.set_footer(text="🎨 Each theme includes unique colors, effects, and visual styling")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="compare_creative", description="Compare two players with creative styling")
    async def compare_creative(self, ctx, player1: discord.Member, player2: discord.Member,
                              theme: str = discord.Option(
                                  description="Theme for comparison",
                                  choices=["auto", "classic", "neon", "cyberpunk", "retro", "ocean"],
                                  default="classic"
                              )):
        """Compare two players with enhanced creative styling"""
        
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
        
        await ctx.response.defer()
        
        try:
            # Convert profiles
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
            
            # Create enhanced comparison embed
            theme_colors = self.profile_generator.color_themes.get(theme, self.profile_generator.color_themes['classic'])
            
            embed = discord.Embed(
                title=f"⚔️ Creative Player Comparison",
                description=f"**{player1.display_name}** vs **{player2.display_name}**\n*Theme: {theme.title()}*",
                color=int(theme_colors['header'].replace('#', ''), 16)
            )
            
            # Performance overview
            p1_avg = sum(p1_stats.values()) / len(p1_stats)
            p2_avg = sum(p2_stats.values()) / len(p2_stats)
            
            winner = "🏆" if p1_avg > p2_avg else ""
            winner2 = "🏆" if p2_avg > p1_avg else ""
            if abs(p1_avg - p2_avg) < 0.5:
                winner = winner2 = "🤝"
            
            embed.add_field(
                name="🎯 Overall Performance",
                value=f"{winner} **{player1.display_name}:** {p1_avg:.1f} avg\n"
                      f"{winner2} **{player2.display_name}:** {p2_avg:.1f} avg",
                inline=False
            )
            
            # Detailed comparison with enhanced formatting
            comparison_text = ""
            stat_labels = {
                'goals_per_game': '⚽ Goals/Game',
                'assists_per_game': '🤝 Assists/Game', 
                'saves_per_game': '🛡️ Saves/Game',
                'shots_per_game': '🎯 Shots/Game',
                'shot_percentage': '📊 Shot %',
                'avg_score': '🏆 Avg Score',
                'win_percentage': '🏅 Win %'
            }
            
            for stat, label in stat_labels.items():
                val1 = p1_stats.get(stat, 0)
                val2 = p2_stats.get(stat, 0)
                
                if val1 > val2:
                    comparison_text += f"{label}: **{val1:.1f}** vs {val2:.1f}\n"
                elif val2 > val1:
                    comparison_text += f"{label}: {val1:.1f} vs **{val2:.1f}**\n"
                else:
                    comparison_text += f"{label}: {val1:.1f} vs {val2:.1f} 🤝\n"
            
            embed.add_field(
                name="📊 Detailed Comparison",
                value=comparison_text,
                inline=False
            )
            
            # Experience comparison
            embed.add_field(
                name="🎮 Experience",
                value=f"**{player1.display_name}:** {p1_dict.get('games_played', 0)} games\n"
                      f"**{player2.display_name}:** {p2_dict.get('games_played', 0)} games",
                inline=True
            )
            
            # Strengths analysis
            p1_best = max(p1_stats.items(), key=lambda x: x[1])
            p2_best = max(p2_stats.items(), key=lambda x: x[1])
            
            embed.add_field(
                name="💪 Top Strengths",
                value=f"**{player1.display_name}:** {stat_labels[p1_best[0]]}\n"
                      f"**{player2.display_name}:** {stat_labels[p2_best[0]]}",
                inline=True
            )
            
            # Verdict with creative flair
            p1_wins = sum(1 for stat in stat_labels.keys() if p1_stats.get(stat, 0) > p2_stats.get(stat, 0))
            p2_wins = sum(1 for stat in stat_labels.keys() if p2_stats.get(stat, 0) > p1_stats.get(stat, 0))
            
            if p1_wins > p2_wins:
                verdict = f"🏆 **{player1.display_name}** dominates in {p1_wins}/{len(stat_labels)} categories!"
            elif p2_wins > p1_wins:
                verdict = f"🏆 **{player2.display_name}** excels in {p2_wins}/{len(stat_labels)} categories!"
            else:
                verdict = "🤝 **Perfectly Matched** - An epic rivalry!"
            
            embed.add_field(
                name="🏁 Final Verdict",
                value=verdict,
                inline=False
            )
            
            embed.set_footer(text=f"🎨 Creative Comparison • Theme: {theme.title()}")
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in creative comparison: {e}")
            await ctx.followup.send("❌ Error generating creative comparison!", ephemeral=True)

def setup(bot):
    bot.add_cog(EnhancedProfilesCog(bot))