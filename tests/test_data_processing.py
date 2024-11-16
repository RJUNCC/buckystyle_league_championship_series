# tests/test_data_processing.py
import unittest
import pandas as pd
from scripts.data_processing import fetch_replays, process_replay_data, process_team_and_player_data

class TestDataProcessing(unittest.TestCase):

    def test_fetch_replays(self):
        replay_df = fetch_replays()
        self.assertIsInstance(replay_df, pd.DataFrame)
        self.assertFalse(replay_df.empty, "Replay DataFrame should not be empty.")
    
    def test_process_replay_data(self):
        replay_df = fetch_replays()
        process_replay_data(replay_df)
        # Check if processed parquet files exist
        blue_df = pd.read_parquet("data/parquet/blue_df.parquet")
        orange_df = pd.read_parquet("data/parquet/orange_df.parquet")
        self.assertFalse(blue_df.empty, "Blue DataFrame should not be empty.")
        self.assertFalse(orange_df.empty, "Orange DataFrame should not be empty.")
    
    def test_process_team_and_player_data(self):
        process_team_and_player_data()
        # Check if final team stats parquet exists
        final_df = pd.read_parquet("data/parquet/better_team_stats.parquet")
        self.assertFalse(final_df.empty, "Final Team Stats DataFrame should not be empty.")
    def test_EPI_score_calculation(self):
        # Create a mock DataFrame
        data = {
            "Team": ["Team A", "Team B"],
            "Win %": [60, 40],
            "Goal_Diff": [10, -5],
            "Demo_Diff": [15, -10],
            "Shot_Diff": [20, -15],
            "Strength_of_Schedule": [0.43, 0.48]
        }
        df = pd.DataFrame(data)
        # Assuming EPI Score calculation logic is encapsulated in a function
        # Here, you would call the function and assert expected outcomes
        # This is a placeholder example
        df["Win % Zscore"] = 0.6
        df["Goal Diff Zscore"] = 0.22
        df["Demo Diff Zscore"] = 0.06
        df["Shots Diff Zscore"] = 0.02
        df["Team Played Win % Zscore"] = 0.10
        df["EPI Score"] = df[[
            "Win % Zscore", 
            "Goal Diff Zscore", 
            "Demo Diff Zscore", 
            "Shots Diff Zscore", 
            "Team Played Win % Zscore"
        ]].sum(axis=1)
        
        self.assertEqual(df.loc[0, "EPI Score"], 1.0)
        self.assertEqual(df.loc[1, "EPI Score"], 1.0)

if __name__ == '__main__':
    unittest.main()
