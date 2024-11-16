# database/database.py
from config.config import Config
import psycopg2
import logging
from psycopg2.extras import RealDictCursor  # For dictionary-like cursor
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Database:
    def __init__(self):
        config = Config()
        try:
            self.connection = psycopg2.connect(
                database=config.database_name,
                user=config.database_user,
                password=config.database_password,
                host=config.database_host,
                port=config.database_port
            )
            self.connection.autocommit = True
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            logging.info("Connected to PostgreSQL database successfully.")
        except psycopg2.Error as e:
            logging.error(f"Failed to connect to the database: {e}")
            raise e

    def fetch_teams(self):
        try:
            query = "SELECT * FROM teams;"
            self.cursor.execute(query)
            teams = self.cursor.fetchall()
            logging.info(f"Fetched {len(teams)} teams from the database.")
            return teams
        except psycopg2.Error as e:
            logging.error(f"Error fetching teams: {e}")
            return []

    def fetch_player_stats(self, player_name: str):
        try:
            query = "SELECT * FROM players WHERE LOWER(name) = LOWER(%s);"
            self.cursor.execute(query, (player_name,))
            player = self.cursor.fetchone()
            if player:
                logging.info(f"Fetched stats for player: {player_name}")
            else:
                logging.info(f"No stats found for player: {player_name}")
            return player
        except psycopg2.Error as e:
            logging.error(f"Error fetching player stats for {player_name}: {e}")
            return None

    def insert_team(self, team_data):
        try:
            query = '''
            INSERT INTO teams (
                name, EPI_Score, EPI_Rank, Games, Win_Percentage, 
                Goals_For, Goals_Against, Goal_Diff, Shots_For, 
                Shots_Against, Shots_Diff, Strength_of_Schedule, 
                Dominance_Quotient
            )
            VALUES (
                %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, 
                %s, %s, %s, 
                %s, %s
            )
            ON CONFLICT (name) DO UPDATE SET
                EPI_Score = EXCLUDED.EPI_Score,
                EPI_Rank = EXCLUDED.EPI_Rank,
                Games = EXCLUDED.Games,
                Win_Percentage = EXCLUDED.Win_Percentage,
                Goals_For = EXCLUDED.Goals_For,
                Goals_Against = EXCLUDED.Goals_Against,
                Goal_Diff = EXCLUDED.Goal_Diff,
                Shots_For = EXCLUDED.Shots_For,
                Shots_Against = EXCLUDED.Shots_Against,
                Shots_Diff = EXCLUDED.Shots_Diff,
                Strength_of_Schedule = EXCLUDED.Strength_of_Schedule,
                Dominance_Quotient = EXCLUDED.Dominance_Quotient;
            '''
            self.cursor.execute(query, team_data)
            logging.info(f"Inserted/Updated team {team_data[0]} in the database.")
        except psycopg2.Error as e:
            logging.error(f"Error inserting/updating team {team_data[0]}: {e}")

    def insert_player(self, player_data):
        try:
            query = '''
            INSERT INTO players (
                name, position, team, points, assists, rebounds, steals, 
                blocks, Strength_of_Schedule
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (name) DO UPDATE SET
                position = EXCLUDED.position,
                team = EXCLUDED.team,
                points = EXCLUDED.points,
                assists = EXCLUDED.assists,
                rebounds = EXCLUDED.rebounds,
                steals = EXCLUDED.steals,
                blocks = EXCLUDED.blocks,
                Strength_of_Schedule = EXCLUDED.Strength_of_Schedule;
            '''
            self.cursor.execute(query, player_data)
            logging.info(f"Inserted/Updated player {player_data[0]} in the database.")
        except psycopg2.Error as e:
            logging.error(f"Error inserting/updating player {player_data[0]}: {e}")

    def fetch_teams_dataframe(self):
        """
        Fetch teams and return as a pandas DataFrame.
        """
        try:
            query = "SELECT * FROM teams;"
            self.cursor.execute(query)
            teams = self.cursor.fetchall()
            df = pd.DataFrame(teams)
            logging.info(f"Fetched {len(df)} teams as DataFrame.")
            return df
        except psycopg2.Error as e:
            logging.error(f"Error fetching teams as DataFrame: {e}")
            return pd.DataFrame()

    def close(self):
        self.cursor.close()
        self.connection.close()
        logging.info("Database connection closed.")
