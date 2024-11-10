# scripts/data_processing.py
import os
import pandas as pd
from scipy.stats import zscore
from discord_bot.utils.database import save_dataframe_to_db
from discord_bot.utils.visualization import create_team_table_image, create_player_data_image
from config.config import Config
import logging

def process_replay_data():
    """
    Process replay data to extract team and player statistics.
    """
    try:
        replay_df = pd.read_parquet("data/parquet/replay_df.parquet")
        logging.info("Loaded replay data.")

        # Define important features
        important_features = ["id", "rocket_league_id", "map_name", "duration", "overtime_seconds", "date", "created", "groups", "blue.name", "blue.goals", "orange.name", "orange.goals"]

        # Process Blue Team Data
        blue_expanded = replay_df[important_features + ['blue.players']].explode('blue.players').reset_index(drop=True)
        blue_expanded['blue_platform'] = blue_expanded['blue.players'].apply(lambda x: x['id']['platform'])
        blue_expanded['blue_player_id'] = blue_expanded['blue.players'].apply(lambda x: x['id']['id'])
        blue_expanded['blue_name'] = blue_expanded['blue.players'].apply(lambda x: x['name'])
        blue_expanded['blue_score'] = blue_expanded['blue.players'].apply(lambda x: x['score'])
        blue_expanded['blue_mvp'] = blue_expanded['blue.players'].apply(lambda x: x.get('mvp', False))
        blue_expanded = blue_expanded.explode('groups').reset_index(drop=True)
        blue_expanded['group_id'] = blue_expanded['groups'].apply(lambda x: x['id'] if isinstance(x, dict) else None)
        blue_df = blue_expanded[blue_expanded['group_id'] != 'all-blcs-2-games-12x79igbdo'].drop(columns=['groups', 'blue.players'])

        # Process Orange Team Data
        orange_expanded = replay_df[important_features + ['orange.players']].explode('orange.players').reset_index(drop=True)
        orange_expanded['orange_platform'] = orange_expanded['orange.players'].apply(lambda x: x['id']['platform'])
        orange_expanded['orange_player_id'] = orange_expanded['orange.players'].apply(lambda x: x['id']['id'])
        orange_expanded['orange_name'] = orange_expanded['orange.players'].apply(lambda x: x['name'])
        orange_expanded['orange_score'] = orange_expanded['orange.players'].apply(lambda x: x['score'])
        orange_expanded['orange_mvp'] = orange_expanded['orange.players'].apply(lambda x: x.get('mvp', False))
        orange_expanded = orange_expanded.explode('groups').reset_index(drop=True)
        orange_expanded['group_id'] = orange_expanded['groups'].apply(lambda x: x['id'] if isinstance(x, dict) else None)
        orange_df = orange_expanded[orange_expanded['group_id'] != 'all-blcs-2-games-12x79igbdo'].drop(columns=['groups', 'orange.players'])

        # Save processed team data
        blue_df.to_parquet("data/parquet/blue_df.parquet")
        orange_df.to_parquet("data/parquet/orange_df.parquet")
        logging.info("Processed team data saved.")

        # Further processing (omitted for brevity)
        # Implement similar steps for player data, team stats, etc.

    except Exception as e:
        logging.error(f"Error processing replay data: {e}")

def calculate_additional_metrics():
    """
    Calculate additional metrics such as Goal Difference, Demos Differential, etc.
    """
    try:
        team_df = pd.read_parquet("data/parquet/better_team_stats.parquet")
        team_df["Goal Diff"] = team_df["Goals For"] - team_df["Goals Against"]
        team_df["Demo Diff"] = team_df["Demos Inflicted"] - team_df["Demos Taken"]
        team_df["Shots Diff"] = team_df["Shots For"] - team_df["Shots Against"]

        # Save updated team stats
        team_df.to_parquet("data/parquet/better_team_stats.parquet")
        logging.info("Additional team metrics calculated and saved.")
    except Exception as e:
        logging.error(f"Error calculating additional metrics: {e}")

def calculate_EPI_scores():
    """
    Calculate EPI Scores based on weighted Z-scores of various metrics.
    """
    try:
        joint = pd.read_parquet("data/parquet/joint_stats.parquet")

        # Define weights
        win_perc_weight = 0.6
        goal_diff_weight = 0.22
        shot_diff_weight = 0.06
        demo_diff_weight = 0.02
        strength_of_schedule = 0.10

        # Calculate Z-scores with weights
        joint["Win % Zscore"] = zscore(joint["Win %"]) * win_perc_weight
        joint["Goal Diff Zscore"] = zscore(joint["Goal Diff"]) * goal_diff_weight
        joint["Demo Diff Zscore"] = zscore(joint["Demo Diff"]) * demo_diff_weight
        joint["Shots Diff Zscore"] = zscore(joint["Shots Diff"]) * shot_diff_weight
        joint["Team Played Win % Zscore"] = zscore(joint["Team Played Win %"]) * strength_of_schedule

        # Calculate EPI Score
        joint["EPI Score"] = joint[["Win % Zscore", "Goal Diff Zscore", "Demo Diff Zscore", "Shots Diff Zscore", "Team Played Win % Zscore"]].sum(axis=1)

        # Rank teams based on EPI Score
        joint["EPI Rank"] = joint["EPI Score"].rank(ascending=False, method="min").astype(int)
        joint = joint.sort_values(by="EPI Rank", ascending=True)

        # Select final columns
        final = joint[["Team", "EPI Score", "Games", "Win %", "Goals For", "Goals Against", "Goal Diff", "Shots For", "Shots Against", "Shot Diff", "Strength of Schedule"]]
        final = final.rename(columns={"Team Played Win %":"Strength of Schedule"})

        # Scale EPI Score
        final["EPI Score"] = round(final["EPI Score"]*50, 2)

        # Format Win %
        final["Win %"] = final["Win %"].astype(int).apply(lambda x: str(f"{x}%") if x > 0 else str(x))

        # Save final team stats
        final.to_parquet("data/parquet/final.parquet")
        logging.info("EPI Scores calculated and final team stats saved.")

    except Exception as e:
        logging.error(f"Error calculating EPI scores: {e}")

def main():
    """
    Main function to run the data processing pipeline.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    process_replay_data()
    calculate_additional_metrics()
    calculate_EPI_scores()

if __name__ == "__main__":
    main()
