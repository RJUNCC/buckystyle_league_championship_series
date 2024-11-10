# discord_bot/utils/database.py
import pandas as pd
from sqlalchemy import create_engine
from config.config import Config

engine = create_engine(Config.DATABASE_URL)

def get_team_stats():
    query = "SELECT * FROM teams ORDER BY EPI_Score DESC"
    teams_df = pd.read_sql(query, engine)
    return teams_df

def get_player_stats():
    query = "SELECT * FROM players"
    players_df = pd.read_sql(query, engine)
    return players_df

def save_dataframe_to_db(df, table_name, if_exists='replace'):
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)

def fetch_dataframe_from_db(query):
    return pd.read_sql(query, engine)
