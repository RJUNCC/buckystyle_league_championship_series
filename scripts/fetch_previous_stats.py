#scripts/fetch_previous_stats.py
import requests
import pandas as pd
from pathlib import Path
import logging
import os
from config.config import Config
from visualization.visualization import make_highlighted_table
from scipy.stats import zscore
import dataframe_image as dfi

config = Config()
#%%
def fetch_previous_player_stats(group_id, token=config._ballchasing_token):
    """
    Fetch previous season stats for all players in the group.
    Args:
        group_id (str): The ID of the group to fetch stats for.
        token (str): The Ballchasing API token.
    Returns:
        pd.DataFrame: A DataFrame containing the player stats.
    """
    url = f"https://ballchasing.com/api/groups/{group_id}"
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    df = pd.json_normalize(data, record_path=["players"])
    return df

def clean_player_data():
    """Clean the data."""

    # Fetch the previous season data
    logging.basicConfig(level=logging.INFO)
    group_id = "all-blcs-games-wvmmrvym05"  # Example group ID
    df = fetch_previous_player_stats(group_id)

    # Clean the data
    df = df.sort_values(by="team").reset_index(drop=True)
    df.loc[9, "cumulative.games"] = df.loc[11, "cumulative.games"]
    df.loc[9, "cumulative.wins"] = df.loc[11, "cumulative.wins"]
    df.loc[9, "cumulative.win_percentage"] = df.loc[11, "cumulative.win_percentage"]
    df.loc[9, "cumulative.play_duration"] = df.loc[11, "cumulative.play_duration"]
    df.loc[9, "cumulative.core.shots_against"] = df.loc[11, "cumulative.core.shots_against"]
    df.loc[9, "cumulative.core.goals_against"] = df.loc[11, "cumulative.core.goals_against"]
    df.loc[9, "cumulative.core.shots"] = df.loc[9, "cumulative.core.shots"] + df.loc[10, "cumulative.core.shots"]
    df.loc[9, "cumulative.core.saves"] = df.loc[9, "cumulative.core.saves"] + df.loc[10, "cumulative.core.saves"]
    df.loc[9, "cumulative.core.assists"] = df.loc[9, "cumulative.core.assists"] + df.loc[10, "cumulative.core.assists"]
    df.loc[9, "cumulative.core.score"] = df.loc[9, "cumulative.core.score"] + df.loc[10, "cumulative.core.score"]
    df.loc[9, "cumulative.boost.amount_stolen_big"] = df.loc[9, "cumulative.boost.amount_stolen_big"] + df.loc[10, "cumulative.boost.amount_stolen_big"]
    df.loc[9, "cumulative.boost.amount_stolen_small"] = df.loc[9, "cumulative.boost.amount_stolen_small"] + df.loc[10, "cumulative.boost.amount_stolen_small"]
    df.loc[9, "game_average.core.score"] = df.loc[9, "cumulative.core.score"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.core.shots"] = df.loc[9, "cumulative.core.shots"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.core.saves"] = df.loc[9, "cumulative.core.saves"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.core.assists"] = df.loc[9, "cumulative.core.assists"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.core.goals"] = df.loc[9, "cumulative.core.goals"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.boost.amount_stolen_big"] = df.loc[9, "cumulative.boost.amount_stolen_big"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.boost.amount_stolen_small"] = df.loc[9, "cumulative.boost.amount_stolen_small"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.demo.inflicted"] = df.loc[9, "cumulative.demo.inflicted"] / df.loc[9, "cumulative.games"]
    df.loc[9, "game_average.demo.taken"] = df.loc[9, "cumulative.demo.taken"] / df.loc[9, "cumulative.games"]

    features_to_keep = [
        "name",
        "team",
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

    df_final = df.drop(10).reset_index(drop=True)
    df_final = df_final[features_to_keep] 
    df_final.columns = ["Player", "Avg Score", "Goals Per Game", "Assists Per Game", "Saves Per Game", "Shots Per Game", "Shooting %", "Demos Inf. Per Game", "Demos Taken Per Game", "Big Boost Stolen", "Small Boost Stolen"]

    return df_final
    

def filter_player_data():
    """Filter the data."""
    # Load the data
    df_final2 = clean_player_data()

    logging.info("Calculating Z-scores and Dominance Quotient for players...")
    df_final2["Avg Score Zscore"] = round(zscore(df_final2["Avg Score"]) * config.avg_score, 2)
    df_final2["Goals Per Game Zscore"] = round(zscore(df_final2["Goals Per Game"]) * config.goals_per_game, 2)
    df_final2["Assists Per Game Zscore"] = round(zscore(df_final2["Assists Per Game"]) * config.assists_per_game, 2)
    df_final2["Saves Per Game Zscore"] = round(zscore(df_final2["Saves Per Game"]) * config.saves_per_game, 2)
    df_final2["Shots Per Game Zscore"] = round(zscore(df_final2["Shots Per Game"]) * config.shots_per_game, 2)
    df_final2["Demos Inf. Per Game Zscore"] = round(zscore(df_final2["Demos Inf. Per Game"]) * config.demos_per_games, 2)
    df_final2["Demos Taken Per Game Zscore"] = round(zscore(df_final2["Demos Taken Per Game"]) * config.demos_taken_per_game, 2)
    df_final2["Big Boost Stolen Zscore"] = round(zscore(df_final2["Big Boost Stolen"]) * config.count_big_pads_stolen_per_game, 2)
    df_final2["Small Boost Stolen Zscore"] = round(zscore(df_final2["Small Boost Stolen"]) * config.count_small_pads_stolen_per_game, 2)

    # for styling purposes
    df_final2["Shooting %"] = df_final2["Shooting %"] / 100

    # Calculate Dominance Quotient
    dq_summation = [i for i in df_final2.columns.tolist() if "Zscore" in i]
    df_final2["Dominance Quotient"] = df_final2[dq_summation].sum(axis=1) * 50
    df_final2 = df_final2[["Player", "Dominance Quotient", "Avg Score", "Goals Per Game", "Assists Per Game", "Saves Per Game", "Shots Per Game", "Shooting %", "Demos Inf. Per Game", "Demos Taken Per Game", "Big Boost Stolen", "Small Boost Stolen"]]
    df_final2 = df_final2.sort_values(by="Dominance Quotient", ascending=False).reset_index(drop=True)
    df_final2.index += 1

    # Save the cleaned data to a parquet file
    df_final2.to_parquet("data/parquet/previous_season_player_data.parquet")

    # highlighted table
    styled_player_df = make_highlighted_table(df_final2)
    image_player_path = Path("images/player_data_blcs_season_1.png")
    image_player_path.parent.mkdir(parents=True, exist_ok=True)
    dfi.export(styled_player_df, image_player_path)
    logging.info(f"Player DataFrame image exported to {image_player_path}")

def main():
    filter_player_data()

if __name__ == "__main__":
    main()