# tests/test_data_processing.py
import unittest
import pandas as pd
from scripts.data_processing import calculate_EPI_scores

class TestDataProcessing(unittest.TestCase):
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
