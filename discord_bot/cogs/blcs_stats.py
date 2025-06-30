# File: discord_bot/cogs/blcs_stats.py

import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import logging
from services.ballchasing_stats_updater import (
    get_ballchasing_updater, sync_blcs_stats, link_discord_to_blcs
)
from models.player_profile import get_player_profile, get_all_profiles

logger = logging.getLogger(__name__)

class BLCSStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="link_blcs", description="Link your Discord to your BLCS ballchasing name")
    async def link_blcs(self, ctx, ballchasing_name: str):
        """Link Discord account to BLCS ballchasing name"""
        
        try:
            # Link the player
            success = link_discord_to_blcs(ctx.author.id, ballchasing_name)
            
            if success:
                embed = discord.Embed(
                    title="✅ BLCS Account Linked!",
                    description=f"Successfully linked your Discord to **{ballchasing_name}**",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="What happens next?",
                    value="• Your stats will be synced from the BLCS ballchasing group\n"
                          "• Use `/sync_blcs_stats` to update immediately\n"
                          "• Your profiles will show live BLCS data\n"
                          "• Stats update automatically during scheduled syncs",
                    inline=False
                )
                
                embed.add_field(
                    name="💡 Tips",
                    value="• Use the **exact** name from ballchasing.com\n"
                          "• Case doesn't matter\n"
                          "• You can check `/blcs_summary` to see all players",
                    inline=False
                )
                
                embed.set_footer(text="BLCS Stats • ballchasing.com integration")
                
            else:
                embed = discord.Embed(
                    title="❌ Link Failed",
                    description="Ballchasing updater not initialized. Please contact an admin.",
                    color=0xff0000
                )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error linking BLCS account: {e}")
            await ctx.respond(f"❌ Error linking account: {str(e)}", ephemeral=True)

    @discord.slash_command(name="sync_blcs_stats", description="[Admin] Sync all BLCS stats from ballchasing.com")
    @commands.has_permissions(administrator=True)
    async def sync_blcs_stats(self, ctx):
        """Manually sync all BLCS stats"""
        
        await ctx.response.defer()
        
        try:
            # Check if updater is available
            updater = get_ballchasing_updater()
            if not updater:
                embed = discord.Embed(
                    title="❌ Service Unavailable",
                    description="Ballchasing updater not initialized. Check bot configuration.",
                    color=0xff0000
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Start sync
            embed = discord.Embed(
                title="🔄 Syncing BLCS Stats...",
                description="Fetching latest data from ballchasing.com group...",
                color=0xffa500
            )
            message = await ctx.followup.send(embed=embed)
            
            # Perform the sync
            updated_count = await sync_blcs_stats()
            
            # Update with results
            if updated_count > 0:
                embed = discord.Embed(
                    title="✅ BLCS Stats Synced!",
                    description=f"Successfully updated **{updated_count}** player profiles",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="📊 What was updated",
                    value="• Games played and win/loss records\n"
                          "• Goals, assists, saves, and shots\n"
                          "• Shooting percentages and averages\n"
                          "• Demo stats and other metrics",
                    inline=False
                )
                
                embed.add_field(
                    name="🎮 Ready to use",
                    value="• `/profile` - Basic profile cards\n"
                          "• `/blcsx_profile` - Advanced BLCSX cards\n"
                          "• `/creative_profile` - Themed profile cards\n"
                          "• `/dominance_leaderboard` - Smart rankings",
                    inline=False
                )
                
            else:
                embed = discord.Embed(
                    title="⚠️ No Updates Applied",
                    description="Either no players are linked or no data was found.",
                    color=0xffa500
                )
                
                embed.add_field(
                    name="Possible reasons:",
                    value="• No players have used `/link_blcs` yet\n"
                          "• Ballchasing.com API issues\n"
                          "• Group has no recent activity\n"
                          "• Player names don't match exactly",
                    inline=False
                )
            
            embed.set_footer(text=f"BLCS Group: blcs-4-qz9e63f182 • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error syncing BLCS stats: {e}")
            embed = discord.Embed(
                title="❌ Sync Failed",
                description=f"Error during sync: {str(e)}",
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="blcs_summary", description="Show BLCS group summary and stats")
    async def blcs_summary(self, ctx):
        """Show summary of BLCS group data"""
        
        await ctx.response.defer()
        
        try:
            updater = get_ballchasing_updater()
            if not updater:
                embed = discord.Embed(
                    title="❌ Service Unavailable",
                    description="Ballchasing updater not initialized.",
                    color=0xff0000
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Get live group summary
            summary = await updater.get_live_group_summary()
            
            if not summary:
                embed = discord.Embed(
                    title="❌ No Data Available",
                    description="Could not fetch BLCS group data from ballchasing.com",
                    color=0xff0000
                )
                await ctx.followup.send(embed=embed)
                return
            
            # Create summary embed
            embed = discord.Embed(
                title="📊 BLCS Group Summary",
                description="Live stats from ballchasing.com group: **blcs-4-qz9e63f182**",
                color=0x0099ff
            )
            
            # Overall stats
            embed.add_field(
                name="📈 Overall Activity",
                value=f"**Players:** {summary['total_players']}\n"
                      f"**Total Games:** {summary['total_games']}\n"
                      f"**Last Updated:** {summary['last_updated']}",
                inline=True
            )
            
            # Top performers
            if summary.get('top_scorer'):
                top_scorer = summary['top_scorer']
                embed.add_field(
                    name="⚽ Top Scorer",
                    value=f"**{top_scorer['name']}**\n"
                          f"{top_scorer['total_goals']} goals in {top_scorer['games_played']} games\n"
                          f"({top_scorer['goals_per_game']:.1f} per game)",
                    inline=True
                )
            
            if summary.get('top_saver'):
                top_saver = summary['top_saver']
                embed.add_field(
                    name="🛡️ Top Saver",
                    value=f"**{top_saver['name']}**\n"
                          f"{top_saver['total_saves']} saves in {top_saver['games_played']} games\n"
                          f"({top_saver['saves_per_game']:.1f} per game)",
                    inline=True
                )
            
            if summary.get('highest_win_rate'):
                top_winner = summary['highest_win_rate']
                embed.add_field(
                    name="🏆 Highest Win Rate",
                    value=f"**{top_winner['name']}**\n"
                          f"{top_winner['win_percentage']:.1f}% win rate\n"
                          f"({top_winner['wins']}W-{top_winner['losses']}L)",
                    inline=True
                )
            
            # Linked players info
            linked_count = len(updater.player_mapping)
            embed.add_field(
                name="🔗 Discord Integration",
                value=f"**Linked Players:** {linked_count}\n"
                      f"**Available Commands:**\n"
                      f"• `/link_blcs` - Link your account\n"
                      f"• `/profile` - View your profile\n"
                      f"• `/blcsx_profile` - Advanced profile",
                inline=False
            )
            
            embed.set_footer(text="🎮 BLCS • Data from ballchasing.com")
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting BLCS summary: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to get BLCS summary: {str(e)}",
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="my_blcs_stats", description="Show your current BLCS stats")
    async def my_blcs_stats(self, ctx):
        """Show user's current BLCS stats"""
        
        try:
            # Get user's profile
            profile = get_player_profile(ctx.author.id)
            
            if not profile:
                embed = discord.Embed(
                    title="❌ No Profile Found",
                    description="You haven't set up a profile yet!",
                    color=0xff0000
                )
                embed.add_field(
                    name="Get Started:",
                    value="1. Use `/link_blcs YourBallchasingName`\n"
                          "2. Admin runs `/sync_blcs_stats`\n"
                          "3. Use `/profile` to see your stats!",
                    inline=False
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Convert profile to dict
            if hasattr(profile, '__dict__'):
                profile_dict = profile.__dict__
            else:
                profile_dict = dict(profile)
            
            # Create stats embed
            embed = discord.Embed(
                title=f"📊 {ctx.author.display_name}'s BLCS Stats",
                description=f"**RL Name:** {profile_dict.get('rl_name', 'Not set')}",
                color=0x0099ff
            )
            
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            
            # Game record
            games_played = profile_dict.get('games_played', 0)
            wins = profile_dict.get('wins', 0)
            losses = profile_dict.get('losses', 0)
            win_rate = (wins / games_played * 100) if games_played > 0 else 0
            
            embed.add_field(
                name="🎮 Game Record",
                value=f"**Games:** {games_played}\n"
                      f"**Record:** {wins}W-{losses}L\n"
                      f"**Win Rate:** {win_rate:.1f}%",
                inline=True
            )
            
            # Offensive stats
            goals = profile_dict.get('total_goals', 0)
            assists = profile_dict.get('total_assists', 0)
            shots = profile_dict.get('total_shots', 0)
            goal_pct = profile_dict.get('goal_percentage', 0)
            
            embed.add_field(
                name="⚽ Offensive Stats",
                value=f"**Goals:** {goals}\n"
                      f"**Assists:** {assists}\n"
                      f"**Shots:** {shots}\n"
                      f"**Goal %:** {goal_pct:.1f}%",
                inline=True
            )
            
            # Defensive stats
            saves = profile_dict.get('total_saves', 0)
            
            embed.add_field(
                name="🛡️ Defensive Stats",
                value=f"**Saves:** {saves}\n"
                      f"**Saves/Game:** {saves/games_played:.1f}" if games_played > 0 else "**Saves:** 0",
                inline=True
            )
            
            # Per-game averages
            if games_played > 0:
                embed.add_field(
                    name="📈 Per Game Averages",
                    value=f"**Score:** {profile_dict.get('total_score', 0)/games_played:.0f}\n"
                          f"**Goals:** {goals/games_played:.1f}\n"
                          f"**Assists:** {assists/games_played:.1f}\n"
                          f"**Saves:** {saves/games_played:.1f}",
                    inline=True
                )
            
            # Update info
            last_updated = profile_dict.get('last_updated')
            if last_updated:
                embed.set_footer(text=f"Last updated: {last_updated}")
            else:
                embed.set_footer(text="Use /sync_blcs_stats to update your stats")
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing BLCS stats: {e}")
            await ctx.respond(f"❌ Error retrieving your stats: {str(e)}", ephemeral=True)

    @discord.slash_command(name="blcs_linked_players", description="[Admin] Show all linked BLCS players")
    @commands.has_permissions(administrator=True)
    async def blcs_linked_players(self, ctx):
        """Show all players linked to BLCS"""
        
        try:
            updater = get_ballchasing_updater()
            if not updater or not updater.player_mapping:
                embed = discord.Embed(
                    title="🔗 BLCS Linked Players",
                    description="No players are currently linked to BLCS.",
                    color=0xffa500
                )
                embed.add_field(
                    name="How to link players:",
                    value="Players use `/link_blcs BallchasingName`",
                    inline=False
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🔗 BLCS Linked Players",
                description=f"**{len(updater.player_mapping)}** players linked to BLCS",
                color=0x00ff00
            )
            
            linked_text = ""
            for discord_id, ballchasing_name in updater.player_mapping.items():
                user = self.bot.get_user(discord_id)
                discord_name = user.display_name if user else f"Unknown ({discord_id})"
                
                # Get profile info
                profile = get_player_profile(discord_id)
                if profile:
                    games = getattr(profile, 'games_played', 0)
                    wins = getattr(profile, 'wins', 0)
                    linked_text += f"**{discord_name}** → {ballchasing_name}\n"
                    linked_text += f"  └ {games} games, {wins} wins\n\n"
                else:
                    linked_text += f"**{discord_name}** → {ballchasing_name}\n"
                    linked_text += f"  └ No stats yet\n\n"
            
            embed.add_field(
                name="Linked Players",
                value=linked_text or "No linked players",
                inline=False
            )
            
            embed.set_footer(text="Use /sync_blcs_stats to update all player stats")
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing linked players: {e}")
            await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(BLCSStatsCog(bot))