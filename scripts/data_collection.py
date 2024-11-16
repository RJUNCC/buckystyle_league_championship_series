# scripts/data_collection.py
import requests
import logging
from config.config import Config
from pathlib import Path
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_replays():
    logging.info("Fetching replay data from Ballchasing API...")
    replay_url = "https://ballchasing.com/api/replays"
    config = Config()
    headers = {"Authorization": config._ballchasing_token}
    params = {'group': "all-blcs-2-games-12x79igbdo"}

    try:
        response = requests.get(replay_url, headers=headers, params=params)
        response.raise_for_status()
        replay_data = response.json()

        # Normalize JSON data
        replay_df = pd.json_normalize(replay_data, record_path=["list"])
        replay_df.to_parquet("data/parquet/replay_df.parquet")
        logging.info("Replay data saved to parquet.")

        return replay_df
    except requests.exceptions.HTTPError as errh:
        logger.error(f"HTTP Error: {errh}")
    except requests.exceptions.ConnectionError as errc:
        logger.error(f"Error Connecting: {errc}")
    except requests.exceptions.Timeout as errt:
        logger.error(f"Timeout Error: {errt}")
    except requests.exceptions.RequestException as err:
        logger.error(f"OOps: Something Else: {err}")

    return None

def main():
    fetch_replays()

if __name__ == "__main__":
    main()
