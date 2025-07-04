# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "dataframe-image",
#     "logging",
#     "pandas",
#     "pyarrow",
#     "python-dotenv",
#     "requests",
#     "scipy",
# ]
# ///
import requests
import pandas as pd
from pathlib import Path
import logging
import os
import sys
from scipy.stats import zscore
import dataframe_image as dfi
import numpy as np
import asyncio
import traceback
# from numpy import round

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import Config
from visualization.visualization import make_highlighted_table, team_styled_table, export_styled_table, create_styled_table

config = Config()

class Process:
    def __init__(self):
        pass


    def fetch_player_data(self, group_id, token=config._ballchasing_token):
        url = f"https://ballchasing.com/api/groups/{group_id}"
        headers = {"Authorization": token}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        df = pd.json_normalize(data, record_path=["players"])
        return df
    
    def fetch_team_data(self, group_id, token=config._ballchasing_token):
        url = f"https://ballchasing.com/api/groups/{group_id}"
        headers = {"Authorization": token}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        df = pd.json_normalize(data, record_path=["teams"])
        return df
    
    def minmax_scale(self, data):
        min_val = np.min(data)
        max_val = np.max(data)
        return (data - min_val) / (max_val - min_val)
    
    def remove_accidental_game(self, df: pd.DataFrame, index: int) -> pd.DataFrame:
        df = df.sort_values('team')
        df.loc[index, 'cumulative.games'] =  df.loc[index-1, 'cumulative.games']
        return df
    

    def process_player_data(self, group_id=config.current_group_id):
        logging.info("Processing player data")
        df = self.fetch_player_data(group_id=group_id)
        features_to_keep = [
            "name",
            "team",
            "cumulative.games",
            "game_average.core.score",
            "game_average.core.goals",
            "game_average.core.assists",
            "game_average.core.saves",
            "game_average.core.shots",
            "game_average.core.shooting_percentage",
            "game_average.demo.inflicted",
            "game_average.demo.taken",
            "game_average.boost.amount_stolen_big",
            "game_average.boost.amount_stolen_small",
        ]

        df = self.remove_accidental_game(df=df, index=11)

        df_final0 = df[features_to_keep].copy()
        df_final0.columns = ["Player", "Team", "Games", "Avg Score", "Goals Per Game", "Assists Per Game", "Saves Per Game", "Shots Per Game", "Shooting %", "Demos Inf. Per Game", "Demos Taken Per Game", "Big Boost Stolen", "Small Boost Stolen"]

        df_final = df_final0.copy()
        # df_final = df_final.drop("Team", axis=1)
        logging.info("Calculating Z-scores and Dominance Quotient for players...")
        df_final["Avg Score Zscore"] = np.round(self.minmax_scale(df_final["Avg Score"]) * config.avg_score, 2)
        df_final["Goals Per Game Zscore"] = np.round(self.minmax_scale(df_final["Goals Per Game"]) * config.goals_per_game, 2)
        df_final["Assists Per Game Zscore"] = np.round(self.minmax_scale(df_final["Assists Per Game"]) * config.assists_per_game, 2)
        df_final["Saves Per Game Zscore"] = np.round(self.minmax_scale(df_final["Saves Per Game"]) * config.saves_per_game, 2)
        df_final["Shots Per Game Zscore"] = np.round(self.minmax_scale(df_final["Shots Per Game"]) * config.shots_per_game, 2)
        df_final["Demos Inf. Per Game Zscore"] = np.round(self.minmax_scale(df_final["Demos Inf. Per Game"]) * config.demos_per_games, 2)
        df_final["Demos Taken Per Game Zscore"] = -np.round(self.minmax_scale(df_final["Demos Taken Per Game"]) * config.demos_taken_per_game, 2)
        df_final["Big Boost Stolen Zscore"] = np.round(self.minmax_scale(df_final["Big Boost Stolen"]) * config.count_big_pads_stolen_per_game, 2)
        df_final["Small Boost Stolen Zscore"] = np.round(self.minmax_scale(df_final["Small Boost Stolen"]) * config.count_small_pads_stolen_per_game, 2)
        df_final["Shooting %"] = df_final["Shooting %"] / 100

        logging.info("Saving to parquet file...")
        print("Saving to parquet file...")
        os.makedirs("data/parquet", exist_ok=True)
        df_final.to_parquet("data/parquet/season_3_all_data.parquet")

        df_final = df_final.drop("Team", axis=1)

        # Calculate Dominance Quotient
        dq_summation = [i for i in df_final.columns.tolist() if "Zscore" in i]
        df_final["Dominance Quotient"] = (df_final[dq_summation].sum(axis=1) + 2) * config.dominance_quotient_multiplier

        df_final = df_final[["Player", "Dominance Quotient", "Avg Score", "Goals Per Game", "Assists Per Game", "Saves Per Game", "Shots Per Game", "Shooting %", "Demos Inf. Per Game", "Demos Taken Per Game", "Big Boost Stolen", "Small Boost Stolen"]]

        df_final = df_final.sort_values(by="Dominance Quotient", ascending=False).reset_index(drop=True)
        df_final.index += 1

        return df_final, df_final0
    
    def merge_remove_duplicate_teams(self, df:pd.DataFrame):
        # Group by the 'Team' column and aggregate numerical columns
        df = df.sort_values('name')

        df["cumulative.games"]

        merged_df = df.groupby("name").agg({   
            "cumulative.games":"sum",       # Sum EPI Score     # Average Roster Rating
            "cumulative.wins":"sum", 
            "cumulative.core.goals": "sum",           # Sum Goals For
            "cumulative.core.goals_against": "sum",       # Sum Goals Against           # Sum Goal Diff
            "cumulative.core.shots": "sum",           # Sum Shots For
            "cumulative.core.shots_against": "sum",
            "cumulative.demo.inflicted": "sum",
            "cumulative.demo.taken": "sum",
            "game_average.core.goals": "sum",
            "game_average.core.goals_against":"sum",
            "game_average.core.shots": "sum",
            "game_average.core.shots_against": "sum"            # Sum Shots Against     # Sum Shot Diff
        }).reset_index()

        print(merged_df.columns)

        merged_df.loc[merged_df.shape[0]-1, 'cumulative.win_percentage'] = merged_df.loc[merged_df.shape[0]-1, 'cumulative.wins'] / merged_df.loc[merged_df.shape[0]-1, 'cumulative.games']

        return merged_df

    def process_team_data(self, group_id=config.current_group_id):
        """Filter the data."""
        team_df = self.fetch_team_data(group_id=group_id)

        # team_df = self.merge_remove_duplicate_teams(team_df)

        team_df = team_df.sort_values('name').reset_index(drop=True)

        # team_df.loc[8, 'cumulative.games'] = team_df.loc[8, 'cumulative.games'] + 1
        # team_df.loc[8, 'cumulative.wins'] = team_df.loc[8, 'cumulative.wins'] + 1
        # team_df.loc[8, 'cumulative.win_percentage'] = team_df.loc[8, 'cumulative.wins'] / team_df.loc[8, 'cumulative.games']*100
        # team_df.loc[8, 'cumulative.core.shots'] = team_df.loc[7, 'cumulative.core.shots'] + team_df.loc[8, 'cumulative.core.shots']
        # team_df.loc[8, 'cumulative.core.shots_against'] = team_df.loc[7, 'cumulative.core.shots_against'] + team_df.loc[8, 'cumulative.core.shots_against']
        # team_df.loc[8, 'cumulative.demo.inflicted'] = team_df.loc[7, 'cumulative.demo.inflicted'] + team_df.loc[8, 'cumulative.demo.inflicted']
        # team_df.loc[8, 'cumulative.demo.taken'] = team_df.loc[7, 'cumulative.demo.taken'] + team_df.loc[8, 'cumulative.demo.taken']
        # team_df.loc[8, 'cumulative.core.goals'] = team_df.loc[7, 'cumulative.core.goals'] + team_df.loc[8, 'cumulative.core.goals']
        # team_df.loc[8, 'cumulative.core.goals_against'] = team_df.loc[7, 'cumulative.core.goals_against'] + team_df.loc[8, 'cumulative.core.goals_against']
        # print(team_df['cumulative.win_percentage'])
        # team_df = team_df.drop(7, axis=0).reset_index(drop=True)
  

        df_final2, df_final = self.process_player_data()
        # Load the data
        team_df = team_df.sort_values(by="name").reset_index(drop=True)
        team_df["Goal Diff"] = team_df["cumulative.core.goals"] - team_df["cumulative.core.goals_against"]
        team_df["Demo Diff"] = team_df["cumulative.demo.inflicted"] / team_df["cumulative.demo.taken"]
        team_df["Shots Diff"] = team_df["cumulative.core.shots"] - team_df["cumulative.core.shots_against"]
        team_df["Demos Inflicted"] = team_df["game_average.demo.inflicted"]
        team_df["Demos Taken"] = team_df["game_average.demo.taken"]
        team_df["Win % Zscore"] = zscore(team_df["cumulative.win_percentage"]) * config.win_perc_weight
        team_df["Goal Diff Zscore"] = zscore(team_df["Goal Diff"]) * config.goal_diff_weight
        team_df["Demo Diff Zscore"] = zscore(team_df["Demo Diff"]) * config.demo_diff_weight
        team_df["Shots Diff Zscore"] = zscore(team_df["Shots Diff"]) * config.shot_diff_weight

        # Calculate EPI Score
        team_df["EPI Score"] = team_df[[
            "Win % Zscore", 
            "Goal Diff Zscore", 
            "Demo Diff Zscore", 
            "Shots Diff Zscore", 
            # "Team Played Win % Zscore"
        ]].sum(axis=1)

        print(team_df)

        features_of_interest = ["name", "cumulative.win_percentage", "game_average.core.goals", "game_average.core.goals_against", "cumulative.core.goals", 
                            "cumulative.core.goals_against", "game_average.core.shots", "game_average.core.shots_against", "cumulative.core.shots", "cumulative.core.shots_against", "EPI Score", "Goal Diff", "Shots Diff", "game_average.demo.inflicted", "game_average.demo.taken"
                            ]
        
        team_df = team_df[features_of_interest]

        team_df = team_df.drop(columns=["cumulative.core.goals", "cumulative.core.goals_against", "cumulative.core.shots", "cumulative.core.shots_against"], axis=1)
        print(team_df)

        team_df.columns = ["Team", "Win %", "Goals For", "Goals Against", "Shots For", "Shots Against", "EPI Score", "Goal Diff", "Shot Diff", "Demos Inflicted", "Demos Taken"]
        print(team_df)

        team_df = team_df[["Team", "EPI Score", "Win %", "Goals For", "Goals Against", "Goal Diff", "Shots For", "Shots Against", "Shot Diff", "Demos Inflicted", "Demos Taken"]]
        print(team_df)

        df_final3 = df_final.copy()
        # print(df_final3.head())
        df_final3["Dominance Quotient"] = df_final3["Player"].map(df_final2.set_index("Player")["Dominance Quotient"])
        df_final3["Dominance Quotient"] = df_final3["Player"].map(df_final2.set_index("Player")["Dominance Quotient"])

        # Calculate Roster Rating
        player_dq_summation = df_final3.groupby("Team")["Dominance Quotient"].sum().reset_index()
        player_dq_summation_zipped = dict(zip(player_dq_summation["Team"], player_dq_summation["Dominance Quotient"]))
        df_final3["Roster Rating"] = df_final3["Team"].map(player_dq_summation_zipped)



        df_final3 = df_final3.drop("Player", axis=1)
        df_final3 = df_final3.groupby("Team")["Roster Rating"].mean().reset_index()

        df_final3 = df_final3.sort_values(by="Roster Rating", ascending=False).reset_index(drop=True)

        team_df = team_df.merge(df_final3, on="Team", how="left")

        team_df["EPI Score"] = round(team_df["EPI Score"] * 50, 2)

        team_df = team_df[["Team", "EPI Score", "Roster Rating", "Win %", "Goals For", "Goals Against", "Goal Diff", "Shots For", "Shots Against", "Shot Diff", "Demos Inflicted", "Demos Taken"]]

        team_df["Goal Diff"] = team_df["Goal Diff"].apply(lambda x: str(f"{x}") if x < 0 else f"+{x}")
        team_df["Shot Diff"] = team_df["Shot Diff"].apply(lambda x: str(f"{x}") if x < 0 else f"+{x}")

        # round win% to no decimal places
        team_df["Win %"] = round(team_df["Win %"]).astype(int)
        team_df["Win %"] = team_df["Win %"].apply(lambda x: f"{x}%")

        for col in team_df.select_dtypes(include="number"):
            if col != "EPI Score":
                team_df[col] = team_df[col].round(2)
            else:
                continue

        team_df = team_df.sort_values(by="EPI Score", ascending=False).reset_index(drop=True)
        team_df.index += 1

        return team_df
    
def run():
    try:
        # Create directories first
        os.makedirs("data/parquet", exist_ok=True)
        os.makedirs("images", exist_ok=True)

        p = Process()

        # Player data
        player_df, _ = p.process_player_data()
        player_path = f"data/parquet/{config.all_player_data}.parquet"
        player_df.to_parquet(player_path)
        print(f"Saved player data to {player_path}")

        # Player image
        styled_player = make_highlighted_table(player_df)
        player_img_path = f"images/{config.all_player_data}.png"
        dfi.export(styled_player, player_img_path, table_conversion="playwright")
        print(f"Generated player image at {player_img_path}")

        # Team data
        team_df = p.process_team_data()
        team_path = f"data/parquet/{config.all_team_data}.parquet"
        team_df.to_parquet(team_path)
        print(f"Saved team data to {team_path}")

        # Team image
        styled_team = team_styled_table(team_df)
        team_img_path = f"images/{config.all_team_data}.png"
        dfi.export(styled_team, team_img_path, table_conversion="playwright")
        print(f"Generated team image at {team_img_path}")

    except Exception as e:
        print(f"CRITICAL ERROR IN PROCESS.PY: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run()