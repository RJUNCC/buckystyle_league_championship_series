# send_images.py

import os
import discord
from discord import File
from dotenv import load_dotenv
from pathlib import Path
import asyncio
import logging

# ======= Setup Logging =======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ======= Load Environment Variables =======
dotenv_path = "../../.env"
load_dotenv(dotenv_path)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID3')

if not DISCORD_TOKEN or not CHANNEL_ID:
    logger.error("DISCORD_TOKEN and CHANNEL_ID must be set in the .env file.")
    exit(1)

try:
    CHANNEL_ID = int(CHANNEL_ID)
    logger.info(f"Configured CHANNEL_ID: {CHANNEL_ID}")
except ValueError:
    logger.error("CHANNEL_ID must be an integer.")
    exit(1)

# ======= Initialize Discord Client =======
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

client = discord.Client(intents=intents)

# ======= Define Image Paths =======
IMAGE_PATHS = [
    "images/playoff_team_data_season_2.png",
    "images/playoff_player_data_season_2.png"
]

# ======= Define Async Function to Remove Previous Messages =======
async def remove_previous_messages(channel):
    """Remove all messages sent by the bot in the specified channel."""
    deleted = 0
    try:
        async for message in channel.history(limit=100):
            if message.author == client.user:
                await message.delete()
                deleted += 1
        logger.info(f"Deleted {deleted} previous messages in channel {CHANNEL_ID}.")
    except Exception as e:
        logger.error(f"Failed to delete previous messages in channel {CHANNEL_ID}: {e}")

# ======= Define Async Function to Send Images =======
async def send_images():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        logger.error(f"Channel with ID {CHANNEL_ID} not found.")
        await client.close()
        return

    # Remove previous messages sent by the bot
    await remove_previous_messages(channel)
    await remove_previous_messages(channel)
    await remove_previous_messages(channel)
    await remove_previous_messages(channel)

    # Send each image
    for image_path in IMAGE_PATHS:
        image_file = Path(image_path)
        if not image_file.is_file():
            logger.warning(f"Image {image_path} does not exist. Skipping.")
            continue
        try:
            with open(image_path, 'rb') as img_file:
                file = File(img_file, filename=image_file.name)
                await channel.send(file=file)
                logger.info(f"Sent image {image_path} to channel {CHANNEL_ID}.")
        except Exception as e:
            logger.error(f"Failed to send image {image_path}: {e}")

    # Disconnect the bot after sending images
    await client.close()
    logger.info("Finished sending images. Disconnecting from Discord.")

# ======= Event: on_ready =======
@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user} (ID: {client.user.id})')
    logger.info('------')
    client.loop.create_task(send_images())

# ======= Run the Bot =======
try:
    client.run(DISCORD_TOKEN)
except Exception as e:
    logger.error(f"An error occurred while running the Discord client: {e}")
