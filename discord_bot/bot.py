# bot.py

import discord
from discord.ext import commands
from config.config import Config
# from discord_bot.cogs.commands import Commands
from discord_bot.cogs.predictions import Predictions
from discord_bot.cogs.schedule import Schedule

import logging

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)

def main():
    config = Config()

    # Define the bot with intents
    intents = discord.Intents.default()
    intents.message_content = True  # Required for reading message content
    bot = commands.Bot(command_prefix='!', intents=intents)

    # Add Schedule Cog
    bot.add_cog(Schedule(bot))

    # Add cogs
    # bot.add_cog(Commands(bot, config))
    # bot.add_cog(Predictions(bot, config))

    # Event: on_ready
    @bot.event
    async def on_ready():
        logging.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
        logging.info('------')

    # Run the bot
    try:
        bot.run(config._discord_token)
    except Exception as e:
        logging.error(f"Failed to run the bot: {e}")

if __name__ == "__main__":
    main()
