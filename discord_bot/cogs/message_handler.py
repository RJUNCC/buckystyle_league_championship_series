# discord_bot/cogs/message_handler.py
from discord.ext import commands
from discord import File
from utils.database import get_team_stats, get_player_stats
from utils.visualization import create_radar_chart, create_kpi_panel
from config.config import Config
from responses import get_response
import pandas as pd
import io

class MessageHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='draft_odds')
    async def draft_odds(self, ctx):
        teams_df = get_team_stats()
        sorted_teams = teams_df.sort_values('EPI_Score').reset_index(drop=True)
        sorted_teams['Draft_Odds (%)'] = (sorted_teams.index + 1) * 2  # Simplified example

        draft_odds_table = sorted_teams[['Team', 'Draft_Odds (%)']].to_markdown(index=False)
        await ctx.send(f"**Draft Odds for Next Season:**\n```{draft_odds_table}```")

    @commands.command(name='predict')
    async def predict(self, ctx, player_name: str):
        players_df = get_player_stats()
        player = players_df[players_df['Player'].str.lower() == player_name.lower()]
        if player.empty:
            await ctx.send(f"Player '{player_name}' not found.")
            return

        player = player.iloc[0]
        radar_img = create_radar_chart(player)
        kpi_img = create_kpi_panel(player)

        files = [
            File(io.BytesIO(radar_img), filename=f"{player['Player']}_radar.png"),
            File(kpi_img, filename=f"{player['Player']}_kpi.png")
        ]

        await ctx.send(
            content=f"**Prediction for {player['Player']}**",
            files=files
        )

    @commands.command(name='send_message')
    async def send_message(self, ctx, *, user_message: str):
        if not user_message:
            await ctx.send("Message was empty.")
            return

        is_private = user_message.startswith('?')
        if is_private:
            user_message = user_message[1:]

        try:
            response = get_response(user_message)
            if is_private:
                await ctx.author.send(response)
            else:
                await ctx.send(response)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            print(e)

def setup(bot):
    bot.add_cog(MessageHandler(bot))
