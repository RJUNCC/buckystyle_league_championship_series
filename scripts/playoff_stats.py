import requests
import pandas as pd
from pathlib import Path
import logging
import os
from config.config import Config
from visualization.visualization import make_highlighted_table, team_styled_table
from scipy.stats import zscore
import dataframe_image as dfi

config = Config()

def fetch_playoff_player_stats(group_id, token=config._ballchasing_token):

    url = f"https://ballchasing.com/api/groups/{group_id}"
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    df = pd.json_normalize(data, record_path=["players"])
    return df

def fetch_playoff_team_stats(group_id, token=config._ballchasing_token):

    url = f"https://ballchasing.com/api/groups/{group_id}"
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    df = pd.json_normalize(data, record_path=["teams"])
    return df

def process():
    df = fetch_playoff_player_stats(config._playoff_group_url)
    
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

    df_final = df[features_to_keep].copy()
    df_final.columns = ["Player", "Team", "Avg Score", "Goals Per Game", "Assists Per Game", "Saves Per Game", "Shots Per Game", "Shooting %", "Demos Inf. Per Game", "Demos Taken Per Game", "Big Boost Stolen", "Small Boost Stolen"]

    df_final2 = df_final.copy()
    df_final2 = df_final2.drop("Team", axis=1)
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
    df_final2["Shooting %"] = df_final2["Shooting %"] / 100

    # Calculate Dominance Quotient
    dq_summation = [i for i in df_final2.columns.tolist() if "Zscore" in i]
    df_final2["Dominance Quotient"] = df_final2[dq_summation].sum(axis=1) * 50

    df_final2 = df_final2[["Player", "Dominance Quotient", "Avg Score", "Goals Per Game", "Assists Per Game", "Saves Per Game", "Shots Per Game", "Shooting %", "Demos Inf. Per Game", "Demos Taken Per Game", "Big Boost Stolen", "Small Boost Stolen"]]

    df_final2 = df_final2.sort_values(by="Dominance Quotient", ascending=False).reset_index(drop=True)
    df_final2.index += 1

    return df_final2, df_final

def filter_player_data():
    """Filter the data."""
    # Load the data
    df_final2, df_final = process()

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
    df_final2.to_parquet("data/parquet/[playoff_player_data_season_2.parquet")

    # highlighted table
    styled_player_df = make_highlighted_table(df_final2)
    image_player_path = Path("images/player_data_blcs_season_2.png")
    image_player_path.parent.mkdir(parents=True, exist_ok=True)
    dfi.export(styled_player_df, image_player_path)
    logging.info(f"Player DataFrame image exported to {image_player_path}")

    return styled_player_df, df_final2, df_final

def filter_team_data():
    """Filter the data."""
    team_df = fetch_playoff_team_stats(group_id=config._playoff_group_url)
    styled_player_data, df_final2, df_final = filter_player_data()
    # Load the data
    team_df = team_df.sort_values(by="name").reset_index(drop=True)
    team_df["Goal Diff"] = team_df["cumulative.core.goals"] - team_df["cumulative.core.goals_against"]
    team_df["Demo Diff"] = team_df["cumulative.demo.inflicted"] - team_df["cumulative.demo.taken"]
    team_df["Shots Diff"] = team_df["cumulative.core.shots"] - team_df["cumulative.core.shots_against"]
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

    features_of_interest = ["name", "cumulative.win_percentage", "game_average.core.goals", "game_average.core.goals_against", "cumulative.core.goals", 
                        "cumulative.core.goals_against", "game_average.core.shots", "game_average.core.shots_against", "cumulative.core.shots", "cumulative.core.shots_against", "EPI Score"
                        ]
    
    team_df = team_df[features_of_interest]

    team_df["Goal Diff"] = team_df.loc[:, "cumulative.core.goals"] - team_df.loc[:, "cumulative.core.goals_against"]
    team_df["Shot Diff"] = team_df.loc[:, "cumulative.core.shots"] - team_df.loc[:, "cumulative.core.shots_against"]

    team_df = team_df.drop(columns=["cumulative.core.goals", "cumulative.core.goals_against", "cumulative.core.shots", "cumulative.core.shots_against"], axis=1)

    team_df.columns = ["Team", "Win %", "Goals For", "Goals Against", "Shots For", "Shots Against", "EPI Score", "Goal Diff", "Shot Diff"]

    team_df = team_df[["Team", "EPI Score", "Win %", "Goals For", "Goals Against", "Goal Diff", "Shots For", "Shots Against", "Shot Diff"]]

    df_final3 = df_final.copy()
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

    team_df = team_df[["Team", "EPI Score", "Roster Rating", "Win %", "Goals For", "Goals Against", "Goal Diff", "Shots For", "Shots Against", "Shot Diff"]]

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

    team_df.to_parquet("data/parquet/playoff_team_data_season_2.parquet")
    team_df.to_csv("data/parquet/playoff_team_data_season_2.csv")

    styled_team_df = team_styled_table(team_df)
    dfi.export(styled_team_df, "images/playoff_team_data_season_2.png")

    return styled_team_df, styled_player_data

if __name__ == "__main__":
    filter_team_data()