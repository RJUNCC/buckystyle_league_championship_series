# cogs/statistics.py
import discord
from discord.ext import commands
import os
import sys
import asyncio
import requests
import json
import time
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.process import Process
from config.config import Config

config = Config()

class StatisticsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.process = Process()
        self.cooldowns = {}
        self.cooldown_time = 300  # 5 minutes cooldown
        
    @discord.slash_command(name="player_statistics")
    async def player_stats(self, ctx, player: discord.Member):
        """View statistics for a specific player"""
        try:
            df, _ = self.process.process_player_data()
            player_stats = df[df['Player'] == player.display_name]
            
            if player_stats.empty:
                return await ctx.respond(f"No statistics found for {player.display_name}", ephemeral=True)

            embed = discord.Embed(title=f"Stats for {player.display_name}", color=discord.Color.blue())
            for column in player_stats.columns:
                if column != 'Player':
                    embed.add_field(name=column, value=player_stats[column].values[0])

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error retrieving player stats: {str(e)}", ephemeral=True)

    @discord.slash_command(name="team_statistics")
    async def team_stats(self, ctx, team_name: str):
        """View statistics for a specific team"""
        try:
            df = self.process.process_team_data()
            team_stats = df[df['Team'] == team_name]
            
            if team_stats.empty:
                return await ctx.respond(f"No statistics found for team {team_name}", ephemeral=True)

            embed = discord.Embed(title=f"Stats for {team_name}", color=discord.Color.green())
            for column in team_stats.columns:
                if column != 'Team':
                    embed.add_field(name=column, value=team_stats[column].values[0])

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error retrieving team stats: {str(e)}", ephemeral=True)

    @discord.slash_command(name="stat_leaderboard")
    async def leaderboard(self, ctx, stat: str):
        """View top players for a specific statistic"""
        try:
            df, _ = self.process.process_player_data()
            if stat not in df.columns:
                return await ctx.respond(f"Invalid statistic. Choose from: {', '.join(df.columns[1:])}", ephemeral=True)

            top_players = df.sort_values(by=stat, ascending=False).head(10)
            
            embed = discord.Embed(title=f"Top Players - {stat}", color=discord.Color.gold())
            for i, (_, player) in enumerate(top_players.iterrows(), 1):
                embed.add_field(name=f"{i}. {player['Player']}", value=f"{player[stat]}", inline=False)

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Error retrieving leaderboard: {str(e)}", ephemeral=True)

    async def verify_workflow_run(self):
        """Check if workflow was actually triggered"""
        url = "https://api.github.com/repos/RJUNCC/buckystyle_league_championship_series/actions/runs"
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                runs = response.json().get('workflow_runs', [])
                if runs and runs[0]['event'] == 'workflow_dispatch':
                    created_at = datetime.strptime(runs[0]['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    return (datetime.utcnow() - created_at).total_seconds() < 60
            return False
        except Exception as e:
            logger.error(f"Workflow verification failed: {str(e)}")
            return False

    def run_workflow(self):
        try:
            # GitHub API endpoint to trigger a workflow
            url = "https://api.github.com/repos/RJUNCC/buckystyle_league_championship_series/actions/workflows/128475690/dispatches"
            headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {os.getenv("GITHUB_TOKEN")}',
                'X-GitHub-Api-Version': '2022-11-28',
                'Content-Type':'application/json'
            }

            # JSON payload with ref and event type
            data = {
                "ref": "main",
            }

            response = requests.post(url=url, headers=headers, data=json.dumps(data))
            if response.status_code == 204:
                logger.info('Successful')
            else:
                logger.error(f'{response.status_code}')
                logger.error('Unsuccessful')
        except requests.exceptions.HTTPError as errh:
            logger.error(f'HTTP Error: {errh}')
        except requests.exceptions.ConnectionError as errc:
            logger.error(f'Error connecting: {errc}')
        except requests.exceptions.Timeout as errt:
            logger.error(f'Timeout Error: {errt}')
        except requests.exceptions.RequestException as err:
            logger.error(f'Something went wrong: {err}')
        except Exception as e:
            logger.error(f'Unexpected error: {str(e)}')


    @discord.slash_command(name="update_all_stats")
    async def update_stats(self, ctx):
        """Trigger GitHub Actions workflow"""
        try:
            await ctx.defer()
            
            # Cooldown check
            user_id = ctx.author.id
            current_time = time.time()
            if user_id in self.cooldowns:
                remaining = self.cooldowns[user_id] + self.cooldown_time - current_time
                if remaining > 0:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    await ctx.followup.send(
                        f"⏳ Command cooldown: {mins}m {secs}s remaining",
                        ephemeral=True
                    )
                    return
            
            # Trigger workflow
            success = self.run_workflow()
            
            if success:
                self.cooldowns[user_id] = current_time
                await ctx.followup.send("✅ Successfully triggered stats update!", ephemeral=True)
            else:
                await ctx.followup.send(
                    "❌ Failed to trigger update. Check logs for details.",
                    ephemeral=True
                )
                
        except Exception as e:
            await ctx.followup.send(f"⚠️ Unexpected error: {str(e)}", ephemeral=True)

    # Keep existing player_stats, team_stats, and leaderboard commands...

def setup(bot):
    bot.add_cog(StatisticsCog(bot))
