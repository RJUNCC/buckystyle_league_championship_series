# send_updates.py
import os
import discord
from discord import Intents, File
from config.config import Config
import pandas as pd
import asyncio
from pathlib import Path
from io import BytesIO
import logging

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)

# Initialize Config
config = Config()

# Initialize Discord Client
intents = Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def remove_previous_image_messages(channel):
    """Remove the last 5 messages sent by the bot in the channel."""
    deleted = 0
    async for message in channel.history(limit=100):
        if message.author == client.user:
            try:
                await message.delete()
                logging.info(f"Deleted message {message.id} in channel {channel.id}")
                deleted += 1
                if deleted >= 5:
                    break
            except Exception as e:
                logging.error(f"Failed to delete message {message.id}: {e}")

async def send_new_image(channel, message_text, image_path):
    """Send a new image to the specified channel."""
    if not Path(image_path).exists():
        logging.warning(f"Image {image_path} does not exist.")
        return
    try:
        await channel.send(message_text, file=File(image_path))
        logging.info(f"Sent image {image_path} to channel {channel.id}")
    except Exception as e:
        logging.error(f"Failed to send image {image_path} to channel {channel.id}: {e}")

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')

    try:
        # Define channels and corresponding images
        channels = [
            (config.channel_id1, "# **Updated team stats**", "../images/table2.png"),
            (config.channel_id2, "# **Updated player data**", "../images/player_data.png"),
        ]

        for channel_id, message_text, image_path in channels:
            channel = client.get_channel(channel_id)
            if channel:
                await remove_previous_image_messages(channel)
                await send_new_image(channel, message_text, image_path)
            else:
                logging.warning(f"Channel ID {channel_id} not found.")
        
        logging.info("All updates sent successfully.")
    except Exception as e:
        logging.error(f"An error occurred during message sending: {e}")
    finally:
        await client.close()
        logging.info("Bot disconnected after sending updates.")

def main():
    # Load and compare dataframes
    final_df_path = "../data/parquet/final.parquet"
    final_player_df_path = "../data/parquet/final_player_data.parquet"
    final_temp_path = "../data/parquet/final_temp.parquet"
    final_player_temp_path = "../data/parquet/final_player_data_temp.parquet"

    main_data_changed = player_data_changed = False

    # Check if temp files exist
    if not os.path.exists(final_temp_path):
        main_data_changed = True
        logging.info(f"{final_temp_path} does not exist. Will create it.")

    if not os.path.exists(final_player_temp_path):
        player_data_changed = True
        logging.info(f"{final_player_temp_path} does not exist. Will create it.")

    # Load current data
    if os.path.exists(final_df_path):
        final_df = pd.read_parquet(final_df_path)
    else:
        logging.error(f"{final_df_path} does not exist.")
        return

    if os.path.exists(final_player_df_path):
        final_player_df = pd.read_parquet(final_player_df_path)
    else:
        logging.error(f"{final_player_df_path} does not exist.")
        return

    # Compare with temp files
    if not main_data_changed and os.path.exists(final_temp_path):
        final_temp_df = pd.read_parquet(final_temp_path)
        main_data_changed = not final_df.equals(final_temp_df)
        if main_data_changed:
            logging.info("Main data has changed.")

    if not player_data_changed and os.path.exists(final_player_temp_path):
        final_player_temp_df = pd.read_parquet(final_player_temp_path)
        player_data_changed = not final_player_df.equals(final_player_temp_df)
        if player_data_changed:
            logging.info("Player data has changed.")

    # Exit early if no changes detected
    if not main_data_changed and not player_data_changed:
        logging.info("No changes detected. Exiting without sending updates.")
        return

    # Update temp files
    if main_data_changed:
        final_df.to_parquet(final_temp_path)
        logging.info(f"Updated {final_temp_path}")

    if player_data_changed:
        final_player_df.to_parquet(final_player_temp_path)
        logging.info(f"Updated {final_player_temp_path}")

    # Run the bot to send updates
    try:
        asyncio.run(client.run(config.discord_token))
    except Exception as e:
        logging.error(f"Failed to run the Discord client: {e}")

if __name__ == "__main__":
    main()
