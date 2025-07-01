# File: discord_bot/cogs/profile_linking.py

import discord
from discord.ext import commands
from services.ballchasing_service import link_discord_to_ballchasing, ballchasing_service
from models.player_profile import get_player_profile, create_or_update_profile

class ProfileLinkingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="link_ballchasing", description="Link your Discord to your ballchasing.com identity")
    async def link_ballchasing(self, ctx, 
                              rl_name: str,
                              steam_id: str = None):
        """Link Discord user to their ballchasing.com identity"""
        
        try:
            # Link the player in the ballchasing service
            link_discord_to_ballchasing(ctx.author.id, rl_name, steam_id)
            
            embed = discord.Embed(
                title="✅ Account Linked!",
                description=f"Successfully linked your Discord to **{rl_name}**",
                color=0x00ff00
            )
            
            embed.add_field(
                name="What happens now?",
                value="• Your stats will auto-update when new replays are uploaded\n"
                      "• Use `/profile` to view your profile card\n"
                      "• Your profile will show live stats from ballchasing.com",
                inline=False
            )
            
            if steam_id:
                embed.add_field(name="Steam ID", value=steam_id, inline=True)
            
            embed.set_footer(text="Stats will update automatically from ballchasing.com replays")
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"❌ Error linking account: {str(e)}", ephemeral=True)

    @discord.slash_command(name="unlink_ballchasing", description="Unlink your ballchasing.com account")
    async def unlink_ballchasing(self, ctx):
        """Unlink user's ballchasing account"""
        
        try:
            # Remove from mapping
            profile = get_player_profile(ctx.author.id)
            if profile and profile.rl_name:
                player_name = profile.rl_name.lower()
                if player_name in ballchasing_service.player_mapping:
                    del ballchasing_service.player_mapping[player_name]
                
                # Update profile to remove ballchasing info
                create_or_update_profile(ctx.author.id, 
                                       steam_id=None,
                                       ballchasing_player_id=None)
                
                embed = discord.Embed(
                    title="✅ Account Unlinked",
                    description="Your ballchasing.com account has been unlinked.",
                    color=0xff9900
                )
                embed.add_field(
                    name="Note",
                    value="Your existing stats will remain, but won't auto-update anymore.",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ No Link Found",
                    description="You don't have a ballchasing.com account linked.",
                    color=0xff0000
                )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"❌ Error unlinking account: {str(e)}", ephemeral=True)

    @discord.slash_command(name="check_link", description="Check if your account is linked to ballchasing.com")
    async def check_link(self, ctx):
        """Check user's ballchasing link status"""
        
        profile = get_player_profile(ctx.author.id)
        
        if not profile:
            embed = discord.Embed(
                title="❌ No Profile Found",
                description="You haven't set up a profile yet. Use `/setup_profile` first.",
                color=0xff0000
            )
        elif profile.rl_name and profile.rl_name.lower() in ballchasing_service.player_mapping:
            embed = discord.Embed(
                title="✅ Account Linked",
                description=f"Your Discord is linked to **{profile.rl_name}**",
                color=0x00ff00
            )
            
            if profile.steam_id:
                embed.add_field(name="Steam ID", value=profile.steam_id, inline=True)
            if profile.last_game_date:
                embed.add_field(
                    name="Last Game", 
                    value=profile.last_game_date.strftime('%m/%d/%Y %H:%M'), 
                    inline=True
                )
            
            embed.add_field(
                name="Auto-Updates",
                value="✅ Enabled - Stats update from ballchasing.com",
                inline=False
            )
        else:
            embed = discord.Embed(
                title="⚠️ Not Linked",
                description="Your account is not linked to ballchasing.com",
                color=0xff9900
            )
            embed.add_field(
                name="To enable auto-updates:",
                value="Use `/link_ballchasing` with your exact in-game name",
                inline=False
            )
        
        await ctx.respond(embed=embed, ephemeral=True)

    # Admin command to link other users
    @discord.slash_command(name="admin_link_player", description="[Admin] Link another player to ballchasing")
    @commands.has_permissions(administrator=True)
    async def admin_link_player(self, ctx,
                               user: discord.Member,
                               rl_name: str,
                               steam_id: str = None):
        """Admin command to link other players"""
        
        try:
            link_discord_to_ballchasing(user.id, rl_name, steam_id, is_admin=True)
            
            embed = discord.Embed(
                title="✅ Player Linked",
                description=f"Successfully linked {user.display_name} to **{rl_name}**",
                color=0x00ff00
            )
            
            await ctx.respond(embed=embed, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"❌ Error linking player: {str(e)}", ephemeral=True)

    @discord.slash_command(name="list_linked_players", description="[Admin] View all linked players")
    @commands.has_permissions(administrator=True)
    async def list_linked_players(self, ctx):
        """Admin command to see all linked players"""
        
        if not ballchasing_service.player_mapping:
            await ctx.respond("❌ No players are currently linked.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔗 Linked Players",
            color=0x0099ff
        )
        
        linked_text = ""
        for rl_name, discord_id in ballchasing_service.player_mapping.items():
            user = self.bot.get_user(int(discord_id))
            discord_name = user.display_name if user else f"Unknown ({discord_id})"
            linked_text += f"**{rl_name.title()}** → {discord_name}\n"
        
        embed.add_field(
            name=f"Total: {len(ballchasing_service.player_mapping)} players",
            value=linked_text,
            inline=False
        )
        
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(ProfileLinkingCog(bot))