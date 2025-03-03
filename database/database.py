import pandas as pd
import sqlite3
import logging
import requests
import os
import sys
from pprint import pprint

# Add the config folder to sys.path
# sys.path.append(os.path.abspath("../config"))

from config import Config

config = Config()

class Database:
    def __init__(self):
        self.db_path = 'data/players.db'
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.setup_tables()

    def setup_tables(self):
        # Create Players table for stats
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Players (
                PlayerID TEXT PRIMARY KEY,
                PlayerName TEXT NOT NULL,
                TeamName TEXT NOT NULL,
                Platform TEXT NOT NULL,
                GamesPlayed INTEGER DEFAULT 0,
                Wins INTEGER DEFAULT 0,
                WinPercentage REAL DEFAULT 0,
                Shots INTEGER DEFAULT 0,
                Goals INTEGER DEFAULT 0,
                Assists INTEGER DEFAULT 0,
                Saves INTEGER DEFAULT 0,
                Score INTEGER DEFAULT 0
            )
        ''')
        # Create DiscordPlayers table for Discord mappings
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS DiscordPlayers (
                DiscordUserID INTEGER PRIMARY KEY,
                PlayerName TEXT NOT NULL,
                PlayerID TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def insert_or_update_player(self, player_data):
        """
        Insert or update player stats in the Players table.
        """
        try:
            # Insert or replace player data
            self.cursor.execute('''
                INSERT INTO Players (PlayerID, PlayerName, TeamName, Platform, GamesPlayed, Wins, WinPercentage, Shots, Goals, Assists, Saves, Score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(PlayerID) DO UPDATE SET
                    PlayerName=excluded.PlayerName,
                    TeamName=excluded.TeamName,
                    Platform=excluded.Platform,
                    GamesPlayed=excluded.GamesPlayed,
                    Wins=excluded.Wins,
                    WinPercentage=excluded.WinPercentage,
                    Shots=excluded.Shots,
                    Goals=excluded.Goals,
                    Assists=excluded.Assists,
                    Saves=excluded.Saves,
                    Score=excluded.Score
            ''', (
                player_data['id'],
                player_data['name'],
                player_data['team'],
                player_data['platform'],
                player_data['cumulative.games'],
                player_data['cumulative.wins'],
                player_data['cumulative.win_percentage'],
                player_data['cumulative.core.shots'],
                player_data['cumulative.core.goals'],
                player_data['cumulative.core.assists'],
                player_data['cumulative.core.saves'],
                player_data['cumulative.core.score']
            ))
            self.conn.commit()
            logging.info(f"Player {player_data['name']} ({player_data['id']}) added/updated successfully.")
        except sqlite3.Error as e:
            logging.error(f"Error inserting/updating player: {e}")

    def fetch_all_players(self):
        """
        Retrieve all players from the Players table.
        """
        self.cursor.execute('SELECT * FROM Players')
        return self.cursor.fetchall()

    def close_connection(self):
        """
        Close the database connection.
        """
        self.conn.close()

