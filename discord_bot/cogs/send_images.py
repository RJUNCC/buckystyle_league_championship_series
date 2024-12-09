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
CHANNEL_ID3 = os.getenv('CHANNEL_ID3')  # Original channel from .env
NEW_CHANNEL_ID = 1291250431619502184  # New channel to send season 2 stats
CHANNEL_S3 = 1307167531173150730

if not DISCORD_TOKEN or not CHANNEL_ID3:
    logger.error("DISCORD_TOKEN and CHANNEL_ID3 must be set in the .env file.")
    exit(1)

try:
    CHANNEL_ID3 = int(CHANNEL_ID3)
    logger.info(f"Configured Original CHANNEL_ID: {CHANNEL_ID3}")
except ValueError:
    logger.error("CHANNEL_ID3 must be an integer.")
    exit(1)

# ======= Initialize Discord Client =======
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

client = discord.Client(intents=intents)

# ======= Define Image Paths for Each Channel =======
IMAGE_PATHS_CHANNEL_ID3 = [
    "../../images/playoff_team_data_season_2.png",
    "../../images/playoff_player_data_season_2.png"
]

IMAGE_PATHS_NEW_CHANNEL = [
    "../../images/season_2_team_styled.png",
    "../../images/season_2_player_styled.png"
]

IMAGE_PATHS_S3_CHANNEL = [
    "../../images/season_2_overall.png",
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
        logger.info(f"Deleted {deleted} previous messages in channel {channel.id}.")
    except Exception as e:
        logger.error(f"Failed to delete previous messages in channel {channel.id}: {e}")

# ======= Define Async Function to Send Images =======
async def send_images_to_channel(channel_id, image_paths):
    """Send images to a specific Discord channel."""
    channel = client.get_channel(channel_id)
    if not channel:
        logger.error(f"Channel with ID {channel_id} not found.")
        return

    # Remove previous messages sent by the bot
    await remove_previous_messages(channel)

    # Send each image
    for image_path in image_paths:
        image_file = Path(image_path)
        if not image_file.is_file():
            logger.warning(f"Image {image_path} does not exist. Skipping.")
            continue
        try:
            with open(image_path, 'rb') as img_file:
                file = File(img_file, filename=image_file.name)
                await channel.send(file=file)
                logger.info(f"Sent image {image_path} to channel {channel_id}.")
        except Exception as e:
            logger.error(f"Failed to send image {image_path}: {e}")

# ======= Async Function to Send Images to All Channels =======
async def send_images():
    await client.wait_until_ready()

    # Send images to the original channel
    await send_images_to_channel(CHANNEL_ID3, IMAGE_PATHS_CHANNEL_ID3)

    # Send images to the new channel
    await send_images_to_channel(NEW_CHANNEL_ID, IMAGE_PATHS_NEW_CHANNEL)

    # Send images to S3 Channel
    await send_images_to_channel(CHANNEL_S3, IMAGE_PATHS_S3_CHANNEL)

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
