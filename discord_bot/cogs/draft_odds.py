# discord_bot/cogs/draft_odds.py
from discord.ext import commands
from utils.database import get_team_stats
import pandas as pd

class DraftOdds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='draft_odds')
    async def draft_odds(self, ctx):
        teams_df = get_team_stats()
        sorted_teams = teams_df.sort_values('EPI_Score').reset_index(drop=True)
        sorted_teams['Draft_Odds (%)'] = (sorted_teams.index + 1) * 2  # Simplified example

        draft_odds_table = sorted_teams[['Team', 'Draft_Odds (%)']].to_markdown(index=False)
        await ctx.send(f"**Draft Odds for Next Season:**\n```{draft_odds_table}```")

def setup(bot):
    bot.add_cog(DraftOdds(bot))
