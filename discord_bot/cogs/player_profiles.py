# File: discord_bot/cogs/player_profiles.py (UPDATED VERSION)

import discord
from discord.ext import commands
from datetime import datetime
from models.player_profile import (
    get_player_profile, create_or_update_profile, 
    get_all_profiles, search_profiles
)

class PlayerProfilesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="profile", description="View a player's Rocket League profile card")
    async def profile(self, ctx, player: discord.Member = None):
        """Display a player's profile card similar to the hockey card you showed"""
        
        # Default to command user if no player specified
        target_user = player if player else ctx.author
        
        # Get profile from database
        profile = get_player_profile(target_user.id)
        
        if not profile:
            if target_user == ctx.author:
                embed = discord.Embed(
                    title="❌ Profile Not Found",
                    description="You haven't set up your profile yet!\n\n**Get Started:**\n• Use `/setup_profile` to create your profile\n• Use `/link_ballchasing` to auto-sync stats",
                    color=0xff0000
                )
            else:
                embed = discord.Embed(
                    title="❌ Profile Not Found", 
                    description=f"{target_user.display_name} hasn't set up their profile yet.",
                    color=0xff0000
                )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        # Create the hockey card style embed
        embed = discord.Embed(
            title=f"🏒 {profile.rl_name or target_user.display_name}",
            color=0x0099ff
        )
        
        # Set user's avatar as thumbnail (like the player photo)
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Player info section (like the hockey card header)
        info_text = f"**Discord:** {target_user.display_name}\n"
        info_text += f"**Age:** {getattr(profile, 'age', 'N/A')}\n"  # You can add age to profile model
        
        if profile.custom_title:
            info_text += f"**Title:** {profile.custom_title}\n"
        if profile.rank_name:
            rank_display = f"{profile.rank_name}"
            if profile.rank_division:
                rank_display += f" {profile.rank_division}"
            if profile.mmr:
                rank_display += f" ({profile.mmr} MMR)"
            info_text += f"**Rank:** {rank_display}\n"
        if profile.favorite_car:
            info_text += f"**Car:** {profile.favorite_car}"
        
        embed.add_field(
            name="👤 Player Info",
            value=info_text,
            inline=True
        )
        
        # Main projection stat (like the big 65% in the center)
        if profile.games_played > 0:
            # Calculate key percentage like goal rate or win rate
            main_percentage = profile.win_percentage
            main_stat_name = "Win Rate"
            
            # Use goal percentage if it's more impressive
            if profile.goal_percentage > profile.win_percentage and profile.total_shots > 10:
                main_percentage = profile.goal_percentage
                main_stat_name = "Goal Rate"
        else:
            main_percentage = 0
            main_stat_name = "No Data"
        
        # Color code the main percentage
        if main_percentage >= 70:
            percentage_color = "🟢"  # Green
        elif main_percentage >= 50:
            percentage_color = "🟡"  # Yellow
        elif main_percentage > 0:
            percentage_color = "🟠"  # Orange
        else:
            percentage_color = "⚪"  # White
        
        embed.add_field(
            name=f"📊 {main_stat_name}",
            value=f"{percentage_color} **{main_percentage:.1f}%**\n\n*Based on {profile.games_played} games*",
            inline=True
        )
        
        # Game situation stats (like the hockey card breakdowns)
        if profile.games_played > 0:
            goals_per_game = profile.total_goals / profile.games_played
            saves_per_game = profile.total_saves / profile.games_played
            assists_per_game = profile.total_assists / profile.games_played
            
            situation_stats = f"**Goals/Game:** {goals_per_game:.1f}\n"
            situation_stats += f"**Saves/Game:** {saves_per_game:.1f}\n"
            situation_stats += f"**Assists/Game:** {assists_per_game:.1f}"
        else:
            situation_stats = "No games played yet"
        
        embed.add_field(
            name="🎯 Per Game Stats",
            value=situation_stats,
            inline=True
        )
        
        # Career totals section
        career_stats = f"**Games:** {profile.games_played}\n"
        career_stats += f"**Record:** {profile.wins}W-{profile.losses}L\n" 
        career_stats += f"**Goals:** {profile.total_goals:,}\n"
        career_stats += f"**Saves:** {profile.total_saves:,}\n"
        career_stats += f"**Assists:** {profile.total_assists:,}\n"
        career_stats += f"**Score:** {profile.total_score:,}"
        
        embed.add_field(
            name="🏆 Career Totals",
            value=career_stats,
            inline=True
        )
        
        # Advanced percentages (like the detailed breakdown)
        if profile.games_played > 5:  # Only show if enough data
            advanced_stats = ""
            
            if profile.total_shots > 0:
                shooting_pct = (profile.total_goals / profile.total_shots) * 100
                advanced_stats += f"**Shooting %:** {shooting_pct:.1f}%\n"
            
            if profile.games_played > 0:
                avg_score = profile.total_score / profile.games_played
                advanced_stats += f"**Avg Score:** {avg_score:.0f}\n"
            
            if profile.total_goals > 0 and profile.total_assists > 0:
                assist_ratio = profile.total_assists / profile.total_goals
                advanced_stats += f"**Assist Ratio:** {assist_ratio:.2f}\n"
            
            # MVP rate if we track it
            if hasattr(profile, 'mvp_count') and profile.mvp_count:
                mvp_rate = (profile.mvp_count / profile.games_played) * 100
                advanced_stats += f"**MVP Rate:** {mvp_rate:.1f}%"
            
            if advanced_stats:
                embed.add_field(
                    name="📈 Advanced Stats",
                    value=advanced_stats,
                    inline=True
                )
        
        # Season stats (if different from career)
        if profile.season_games > 0:
            season_stats = f"**Season:** {profile.current_season}\n"
            season_stats += f"**Games:** {profile.season_games}\n"
            season_stats += f"**Record:** {profile.season_wins}W-{profile.season_games - profile.season_wins}L\n"
            season_stats += f"**Goals:** {profile.season_goals}\n"
            season_stats += f"**Saves:** {profile.season_saves}"
            
            embed.add_field(
                name="🗓️ Current Season",
                value=season_stats,
                inline=True
            )
        
        # Footer with last updated (like the data source)
        footer_text = ""
        if profile.last_game_date:
            footer_text += f"Last Game: {profile.last_game_date.strftime('%m/%d/%Y')}"
        if profile.last_updated:
            if footer_text:
                footer_text += " • "
            footer_text += f"Updated: {profile.last_updated.strftime('%m/%d/%Y %H:%M')}"
        
        embed.set_footer(text=footer_text)
        
        # Color coding based on performance (like the hockey card colors)
        if profile.win_percentage >= 70:
            embed.color = 0x00ff00  # Green for elite
        elif profile.win_percentage >= 60:
            embed.color = 0x99ff00  # Light green for above average
        elif profile.win_percentage >= 50:
            embed.color = 0xffff00  # Yellow for average
        elif profile.win_percentage >= 40:
            embed.color = 0xff9900  # Orange for below average
        elif profile.games_played > 0:
            embed.color = 0xff3300  # Red for poor performance
        else:
            embed.color = 0x999999  # Gray for no data
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="setup_profile", description="Set up or update your Rocket League profile")
    async def setup_profile(self, ctx, rl_name: str, platform: str, age: int, favorite_car: str, custom_title: str = None):
        """Set up your player profile with stats and custom info."""
        try:
            profile_data = {
                'rl_name': rl_name,
                'ballchasing_platform': platform.lower(),
                'age': age,
                'favorite_car': favorite_car,
                'custom_title': custom_title,
                'discord_username': ctx.author.name
            }
            
            # This will create or update the profile
            profile = create_or_update_profile(ctx.author.id, **profile_data)
            
            embed = discord.Embed(
                title="✅ Profile Setup Successful!",
                description=f"Your profile for **{profile.rl_name}** has been created/updated.",
                color=0x00ff00
            )
            embed.add_field(name="Rocket League Name", value=profile.rl_name, inline=True)
            embed.add_field(name="Platform", value=profile.ballchasing_platform.capitalize(), inline=True)
            embed.add_field(name="Age", value=str(profile.age), inline=True)
            embed.add_field(name="Favorite Car", value=profile.favorite_car, inline=True)
            if profile.custom_title:
                embed.add_field(name="Custom Title", value=profile.custom_title, inline=True)
            
            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            # Shorten the error message to avoid exceeding Discord's character limit
            error_message = str(e)
            if len(error_message) > 1500:
                error_message = error_message[:1500] + "... (message truncated)"
            await ctx.respond(f"❌ Error setting up profile: {error_message}", ephemeral=True)

    @discord.slash_command(name="leaderboard", description="View the league leaderboard")
    async def leaderboard(self, ctx, stat: str = "wins"):
        """Show leaderboard for different stats"""
        
        valid_stats = ["wins", "goals", "saves", "win_rate", "goal_rate", "games", "score"]
        if stat not in valid_stats:
            await ctx.respond(f"❌ Invalid stat. Choose from: {', '.join(valid_stats)}", ephemeral=True)
            return
        
        profiles = get_all_profiles()
        
        if not profiles:
            await ctx.respond("❌ No profiles found in the database.", ephemeral=True)
            return
        
        # Sort profiles based on selected stat
        if stat == "wins":
            sorted_profiles = sorted(profiles, key=lambda p: p.wins, reverse=True)
            stat_display = "Wins"
        elif stat == "goals":
            sorted_profiles = sorted(profiles, key=lambda p: p.total_goals, reverse=True)
            stat_display = "Goals"
        elif stat == "saves":
            sorted_profiles = sorted(profiles, key=lambda p: p.total_saves, reverse=True)
            stat_display = "Saves"
        elif stat == "win_rate":
            sorted_profiles = sorted([p for p in profiles if p.games_played >= 5], 
                                   key=lambda p: p.win_percentage, reverse=True)
            stat_display = "Win Rate (5+ games)"
        elif stat == "goal_rate":
            sorted_profiles = sorted([p for p in profiles if p.total_shots >= 10], 
                                   key=lambda p: p.goal_percentage, reverse=True)
            stat_display = "Goal Rate (10+ shots)"
        elif stat == "games":
            sorted_profiles = sorted(profiles, key=lambda p: p.games_played, reverse=True)
            stat_display = "Games Played"
        elif stat == "score":
            sorted_profiles = sorted(profiles, key=lambda p: p.total_score, reverse=True)
            stat_display = "Total Score"
        
        embed = discord.Embed(
            title=f"🏆 Leaderboard - {stat_display}",
            color=0xffd700
        )
        
        leaderboard_text = ""
        for i, profile in enumerate(sorted_profiles[:10], 1):  # Top 10
            # Get Discord user
            user = self.bot.get_user(int(profile.discord_id))
            display_name = user.display_name if user else profile.discord_username
            
            # Get stat value
            if stat == "wins":
                value = f"{profile.wins}"
            elif stat == "goals":
                value = f"{profile.total_goals}"
            elif stat == "saves":
                value = f"{profile.total_saves}"
            elif stat == "win_rate":
                value = f"{profile.win_percentage:.1f}%"
            elif stat == "goal_rate":
                value = f"{profile.goal_percentage:.1f}%"
            elif stat == "games":
                value = f"{profile.games_played}"
            elif stat == "score":
                value = f"{profile.total_score:,}"
            
            # Medal emojis for top 3
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            leaderboard_text += f"{medal} **{display_name}** - {value}\n"
        
        embed.add_field(
            name=f"Top Players",
            value=leaderboard_text or "No qualifying players found",
            inline=False
        )
        
        embed.set_footer(text=f"Showing top {min(len(sorted_profiles), 10)} players")
        
        await ctx.respond(embed=embed)

    @discord.slash_command(name="find_player", description="Search for a player's profile")
    async def find_player(self, ctx, search_term: str):
        """Search for players by name"""
        
        profiles = search_profiles(search_term)
        
        if not profiles:
            await ctx.respond(f"❌ No players found matching '{search_term}'", ephemeral=True)
            return
        
        if len(profiles) == 1:
            # If only one result, show their profile
            profile = profiles[0]
            user = self.bot.get_user(int(profile.discord_id))
            if user:
                await self.profile(ctx, player=user)
            else:
                await ctx.respond("❌ Could not find Discord user for this profile.", ephemeral=True)
        else:
            # Multiple results, show list
            embed = discord.Embed(
                title=f"🔍 Search Results for '{search_term}'",
                color=0x0099ff
            )
            
            results_text = ""
            for profile in profiles[:10]:  # Show up to 10 results
                user = self.bot.get_user(int(profile.discord_id))
                display_name = user.display_name if user else profile.discord_username
                rl_name = profile.rl_name if profile.rl_name else "No RL name"
                
                results_text += f"**{display_name}** ({rl_name})\n"
                results_text += f"  └ {profile.wins}W-{profile.losses}L, {profile.total_goals} goals\n\n"
            
            embed.add_field(
                name="Players Found",
                value=results_text,
                inline=False
            )
            
            embed.set_footer(text="Use /profile @user to view a specific player's profile")
            
            await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(PlayerProfilesCog(bot))