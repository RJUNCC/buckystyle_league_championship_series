# discord_bot/bot.py
import discord
from discord.ext import commands, tasks
from config.config import Config
from utils.database import get_team_stats, get_player_stats
from utils.visualization import create_radar_chart, create_kpi_panel
import pandas as pd
import io
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load cogs
initial_extensions = [
    'cogs.draft_odds', 
    'cogs.predictions',
    'cogs.team_stats'
]

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
            print(f'Loaded extension {extension}')
        except Exception as e:
            print(f'Failed to load extension {extension}.')
            print(e)

    bot.run(Config.DISCORD_BOT_TOKEN)
