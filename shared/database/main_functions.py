import pandas as pd
import requests
from .database import Database
import os
import sys

# Add the config folder to sys.path
sys.path.append(os.path.abspath("../config"))

from config import Config

config = Config()
db = Database()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

def fetch_player_data(group_id=config.current_group_id, token=config._ballchasing_token):
    """
    Fetch player data from Ballchasing API.

    Args:
    group_id (str): The group ID from Ballchasing.
    token (str): API token for authentication.

    Returns:
    pd.DataFrame: A DataFrame containing normalized player data.
    """
    url = f"https://ballchasing.com/api/groups/{group_id}"
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Parse JSON response and normalize into a DataFrame
    data = response.json()
    df = pd.json_normalize(data, record_path=["players"])
    
    return df

def get_access_token(code):
    """
    Exchange authorization code for an access token.
    """
    url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=data, headers=headers)
    return response.json()

def get_user_connections(access_token):
    """
    Fetch a user's connected accounts (e.g., Steam/Epic) using their access token.
    """
    url = "https://discord.com/api/users/@me/connections"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    return response.json()

def process_ballchasing_data(df, db: Database):
    """
    Process and store Ballchasing data into the database.
    
    Args:
    df (pd.DataFrame): DataFrame containing Ballchasing data.
    db (Database): Instance of the Database class.
    """
    for _, row in df.iterrows():
        # Convert row to dictionary
        player_data = row.to_dict()

        # Insert or update each player's stats in the database
        db.insert_or_update_player(player_data)

def init_db():
    df = fetch_player_data()
    process_ballchasing_data(df, db) 

def get_players():
    players = db.fetch_all_players()
    print(players)

def match_players(ballchasing_df, player_mappings):
    """
    Match Ballchasing players with Discord users based on player name or connected accounts.
    """
    matched_players = []
    unmatched_players = []

    for _, row in ballchasing_df.iterrows():
        player_name = row["name"]
        steam_or_epic_id = row["id"]

        # Attempt to find a match in player_mappings
        matched_user = next(
            (
                user_id
                for user_id, mapping in player_mappings.items()
                if mapping["PlayerName"].lower() == player_name.lower()
            ),
            None,
        )

        if matched_user:
            matched_players.append((matched_user, steam_or_epic_id))
        else:
            unmatched_players.append(player_name)

    return matched_players, unmatched_players