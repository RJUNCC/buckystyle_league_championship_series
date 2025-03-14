# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "discord",
#     "logging",
#     "pathlib",
#     "python-dotenv",
# ]
# ///
import os
import discord
from discord import File
from dotenv import load_dotenv
from pathlib import Path
import asyncio
import logging
import sys

current_dir = os.path.dirname(os.path.abspath("__file__"))
print(current_dir)
parent_dir = os.path.abspath(os.path.join(current_dir, '.'))
print(parent_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from config.config import Config

config = Config()

# ======= Setup Logging =======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ======= Load Environment Variables =======
# dotenv_path = ".env"
# load_dotenv(dotenv_path)
# print(f"LOADING{load_dotenv(dotenv_path)}")

DISCORD_TOKEN = config._discord_token
PLAYER_CHANNEL_ID = config._player_channel_id # Original channel from .env
TEAM_CHANNEL_ID = config._team_channel_id
PLAYOFF_CHANNEL_ID = os.getenv('PLAYOFF_CHANNEL_ID')

if not DISCORD_TOKEN or not PLAYER_CHANNEL_ID or not TEAM_CHANNEL_ID:
    logger.error("DISCORD_TOKEN, PLAYER_CHANNEL_ID, and TEAM_CHANNEL_ID must be set in the .env file.")
    exit(1)

try:
    PLAYER_CHANNEL_ID = int(PLAYER_CHANNEL_ID)
    TEAM_CHANNEL_ID = int(TEAM_CHANNEL_ID)
    logger.info(f"Configured CHANNEL_IDs: Player: {PLAYER_CHANNEL_ID}, Team: {TEAM_CHANNEL_ID}")
except ValueError:
    logger.error("PLAYER_CHANNEL_ID and TEAM_CHANNEL_ID must be integers.")
    exit(1)

# ======= Initialize Discord Client =======
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.guilds = True           # Ensure guild-related intents are enabled
intents.guild_messages = True   # Access to guild messages

client = discord.Client(intents=intents)

# ======= Define Image Paths for Each Channel =======
IMAGE_PATHS_PLAYER_CHANNEL = [
    f"images/{config.all_player_data}.png",
    # "../../images/worlds.png",
]

IMAGE_PATHS_TEAM_CHANNEL = [
    f"images/{config.all_team_data}.png",
]

IMAGE_PATHS_PLAYOFF_STATS = [
    f"images/{config.playoff_player_path}.png",
    f"images/{config.playoff_team_path}.png",
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
    try:
        channel = client.get_channel(channel_id)
        if not channel:
            # Attempt to fetch the channel if it's not in the cache
            channel = await client.fetch_channel(channel_id)
    except discord.NotFound:
        logger.error(f"Channel with ID {channel_id} not found.")
        return
    except discord.Forbidden:
        logger.error(f"Bot does not have access to channel with ID {channel_id}.")
        return
    except discord.HTTPException as e:
        logger.error(f"Failed to fetch channel {channel_id}: {e}")
        return

    if not channel:
        logger.error(f"Channel with ID {channel_id} not found after fetching.")
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

    logging.info("Sending images to Player Channel...")
    await send_images_to_channel(PLAYER_CHANNEL_ID, IMAGE_PATHS_PLAYER_CHANNEL)

    # Send images to the team channel
    logging.info("Sending images to Team Channel...")
    await send_images_to_channel(TEAM_CHANNEL_ID, IMAGE_PATHS_TEAM_CHANNEL)

    # Send images to playoff chnanel
    # logging.info("Sending images to playoff channel")
    # await send_images_to_channel(PLAYOFF_CHANNEL_ID, IMAGE_PATHS_PLAYOFF_STATS)

    # Disconnect the bot after sending images
    await client.close()
    logger.info("Finished sending images. Disconnecting from Discord.")

# ======= Event: on_ready =======
@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user} (ID: {client.user.id})')
    logger.info('------')
    
    # List all accessible channels for debugging
    for guild in client.guilds:
        logger.info(f"Guild: {guild.name} (ID: {guild.id})")
        for channel in guild.channels:
            logger.info(f" - Channel: {channel.name} (ID: {channel.id})")
    
    client.loop.create_task(send_images())

# ======= Run the Bot =======
try:
    client.run(DISCORD_TOKEN)
except Exception as e:
    logger.error(f"An error occurred while running the Discord client: {e}")