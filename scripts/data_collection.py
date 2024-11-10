# scripts/data_collection.py
import os
import pandas as pd
import requests
from dotenv import load_dotenv
from config.config import Config
import logging

def fetch_replays():
    """
    Fetch replay data from BallChasing API.
    """
    try:
        url = "https://ballchasing.com/api/replays"
        headers = {"Authorization": Config.BALLCHASING_TOKEN}
        params = {'group': "all-blcs-2-games-12x79igbdo"}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        logging.info("Successfully fetched replay data.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching replays: {e}")
        return None

def save_replay_data(data):
    """
    Save replay data to a Parquet file.
    """
    if data and 'list' in data:
        replay_df = pd.json_normalize(data, record_path=["list"])
        os.makedirs("data/parquet", exist_ok=True)
        replay_df.to_parquet("data/parquet/replay_df.parquet")
        logging.info("Replay data saved to data/parquet/replay_df.parquet")
    else:
        logging.warning("No replay data to save.")

def main():
    """
    Main function to fetch and save replay data.
    """
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    data = fetch_replays()
    save_replay_data(data)

if __name__ == "__main__":
    main()
