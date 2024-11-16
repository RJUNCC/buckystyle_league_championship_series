# scripts/data_processing.py

import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv
import os
from pprint import pprint
from bs4 import BeautifulSoup
from scipy.stats import zscore
import dataframe_image as dfi
import logging
from pathlib import Path

def setup_logging():
    """Configure logging for the script."""
    log_dir = Path("../logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "data_processing.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )

def load_environment():
    """Load environment variables from the .env file."""
    load_dotenv("../.env")
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        logging.error("TOKEN not found in environment variables.")
        raise EnvironmentError("TOKEN not found in environment variables.")
    logging.info("Environment variables loaded successfully.")
    return TOKEN

def fetch_replay_data(token):
    """Fetch replay data from Ballchasing API and save it as a Parquet file."""
    logging.info("Fetching replay data from Ballchasing API...")
    actual_replay_url = "https://ballchasing.com/api/replays"
    replay_headers = {
        "Authorization": token
    }
    replay_params = {
        'group': "all-blcs-2-games-12x79igbdo",
    }
    
    try:
        replay_response = requests.get(actual_replay_url, headers=replay_headers, params=replay_params)
        replay_response.raise_for_status()
        logging.info(f"Replay data fetched successfully with status code {replay_response.status_code}.")
    except requests.exceptions.HTTPError as errh:
        logging.error(f"HTTP Error: {errh}")
        raise
    except requests.exceptions.ConnectionError as errc:
        logging.error(f"Error Connecting: {errc}")
        raise
    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout Error: {errt}")
        raise
    except requests.exceptions.RequestException as err:
        logging.error(f"OOps: Something Else: {err}")
        raise
    
    replay_df = pd.json_normalize(
        replay_response.json(),
        record_path=["list"]
    )
    
    replay_parquet_path = Path("../data/parquet/replay_df.parquet")
    replay_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    replay_df.to_parquet(replay_parquet_path)
    logging.info(f"Replay data saved to {replay_parquet_path}")
    return replay_df

def process_team_players(replay_df, team_color):
    """
    Process either blue or orange team data.
    
    Parameters:
    - replay_df: DataFrame containing replay data.
    - team_color: 'blue' or 'orange' indicating which team's data to process.
    
    Returns:
    - Processed DataFrame for the specified team.
    """
    logging.info(f"Processing {team_color} team data...")
    important_features = ["id", "rocket_league_id", "map_name", "duration", 
                         "overtime_seconds", "date", "created", "groups", 
                         f"{team_color}.name", f"{team_color}.goals"]
    
    expanded_df = replay_df[important_features + [f'{team_color}.players']].explode(f'{team_color}.players').reset_index(drop=True)
    logging.debug(f"Exploded {team_color}.players column.")
    
    expanded_df[f'{team_color}_platform'] = expanded_df[f'{team_color}.players'].apply(lambda x: x['id']['platform'])
    expanded_df[f'{team_color}_player_id'] = expanded_df[f'{team_color}.players'].apply(lambda x: x['id']['id'])
    expanded_df[f'{team_color}_name'] = expanded_df[f'{team_color}.players'].apply(lambda x: x['name'])
    expanded_df[f'{team_color}_score'] = expanded_df[f'{team_color}.players'].apply(lambda x: x['score'])
    expanded_df[f'{team_color}_mvp'] = expanded_df[f'{team_color}.players'].apply(lambda x: x.get('mvp', False))  # MVP may be absent for some players
    
    logging.debug(f"Flattened {team_color}.players data.")
    
    expanded_df = expanded_df.explode('groups').reset_index(drop=True)
    logging.debug(f"Exploded 'groups' column for {team_color} team.")
    
    expanded_df['group_id'] = expanded_df['groups'].apply(lambda x: x['id'] if isinstance(x, dict) else None)
    expanded_df = expanded_df[expanded_df['group_id'] != 'all-blcs-2-games-12x79igbdo']
    logging.debug(f"Filtered out unwanted group_ids for {team_color} team.")
    
    processed_df = expanded_df.drop(columns=['groups', f'{team_color}.players'])
    parquet_path = Path(f"../data/parquet/{team_color}_df.parquet")
    processed_df.to_parquet(parquet_path)
    logging.info(f"{team_color.capitalize()} team data processed and saved to {parquet_path}")
    
    return processed_df

def fetch_group_data(token):
    """Fetch group data from Ballchasing API and save it as a Parquet file."""
    logging.info("Fetching group data from Ballchasing API...")
    replay_url = "https://ballchasing.com/api/groups/all-blcs-2-games-12x79igbdo"
    headers = {
        'Authorization': token
    }
    
    try:
        response = requests.get(replay_url, headers=headers)
        response.raise_for_status()
        logging.info(f"Group data fetched successfully with status code {response.status_code}.")
    except requests.exceptions.HTTPError as errh:
        logging.error(f"HTTP Error: {errh}")
        raise
    except requests.exceptions.ConnectionError as errc:
        logging.error(f"Error Connecting: {errc}")
        raise
    except requests.exceptions.Timeout as errt:
        logging.error(f"Timeout Error: {errt}")
        raise
    except requests.exceptions.RequestException as err:
        logging.error(f"OOps: Something Else: {err}")
        raise
    
    json_data = response.json()
    df = pd.json_normalize(
        json_data,
        record_path=["players"],
    )
    
    logging.debug("Normalized group data JSON into DataFrame.")
    df = df.sort_values(by="name")
    
    # Manual adjustments to specific rows
    adjustments = [
        (14, {"cumulative.games": -1, "cumulative.wins": -1, "cumulative.win_percentage": df.loc[6, "cumulative.win_percentage"],
              "cumulative.play_duration": df.loc[6, "cumulative.play_duration"],
              "cumulative.core.shots_against": df.loc[6, "cumulative.core.shots_against"],
              "game_average.core.goals_against": df.loc[6, "game_average.core.goals_against"],
              "game_average.core.shots_against": df.loc[6, "game_average.core.shots_against"]}),
        (7, {"cumulative.games": -1, "cumulative.win_percentage": df.loc[2, "cumulative.win_percentage"],
             "cumulative.play_duration": df.loc[2, "cumulative.play_duration"],
             "cumulative.core.shots_against": df.loc[2, "cumulative.core.shots_against"],
             "game_average.core.goals_against": df.loc[2, "game_average.core.goals_against"],
             "game_average.core.shots_against": df.loc[2, "game_average.core.shots_against"]})
    ]
    
    for index, changes in adjustments:
        for column, change in changes.items():
            if isinstance(change, (int, float)):
                df.loc[index, column] = df.loc[index, column] + change
                logging.debug(f"Adjusted {column} for row {index} by {change}.")
            else:
                df.loc[index, column] = change
                logging.debug(f"Set {column} for row {index} to {change}.")
    
    team_dicts = {
        "BECKYARDIGANS": "BECKYARDIGANS",
        "KILLER": "KILLER B'S",
        "DIDDLERS":"DIDDLERS",
        "EXECUTIVE": "EXECUTIVE PROJEC",
        "MINORITIES":"MINORITIES",
        "PUSHIN":"PUSHIN PULLIS",
        "SCAVS":"SCAVS",
        "WONDER":"WONDER PETS"
    }
    
    # Aggregations
    logging.info("Performing aggregations on group data...")
    team_goals_df = df.groupby('team')["cumulative.core.goals"].sum().reset_index()
    team_goals_against = dict(zip(df["team"], df["cumulative.core.goals_against"]))
    team_goals = dict(zip(team_goals_df["team"], team_goals_df["cumulative.core.goals"]))
    
    demos_inflicted_df = df.groupby("team")["cumulative.demo.inflicted"].sum().reset_index()
    demos_taken_df = df.groupby("team")["cumulative.demo.taken"].sum().reset_index()
    
    demos_inflicted = dict(zip(demos_inflicted_df["team"], demos_inflicted_df["cumulative.demo.inflicted"]))
    demos_taken = dict(zip(demos_taken_df["team"], demos_taken_df["cumulative.demo.taken"]))
    
    shots_for_df = df.groupby("team")["cumulative.core.shots"].sum().reset_index()
    shots_against_df = df.groupby('team')["cumulative.core.shots_against"].sum().reset_index()
    
    shots_for = dict(zip(shots_for_df["team"], shots_for_df["cumulative.core.shots"]))
    shots_against = dict(zip(df["team"], df["cumulative.core.shots_against"]))
    
    final_df = pd.DataFrame(df["team"].unique(), columns=["Team"])
    
    final_df["Win %"] = final_df["Team"].map(dict(zip(df["team"], df["cumulative.win_percentage"])))
    final_df["Games"] = final_df["Team"].map(dict(zip(df["team"], df["cumulative.games"])))
    final_df["Wins"] = final_df["Team"].map(dict(zip(df["team"], df["cumulative.wins"])))
    final_df["Goals For"] = final_df["Team"].map(team_goals)
    final_df["Goals Against"] = final_df["Team"].map(team_goals_against)
    final_df["Shots For"] = final_df["Team"].map(shots_for)
    final_df["Shots Against"] = final_df["Team"].map(shots_against)
    final_df["Demos Inflicted"] = final_df["Team"].map(demos_inflicted)
    final_df["Demos Taken"] = final_df["Team"].map(demos_taken)
    
    df["team"] = df["team"].str.replace("'", "", regex=True)
    
    os.makedirs("../data/excel_files", exist_ok=True)
    final_df.to_parquet("../data/parquet/better_team_stats.parquet")
    df.to_parquet("../data/parquet/player_data.parquet")
    logging.info("Team and player data saved to Parquet files.")
    
def calculate_diffs_and_wins():
    """Calculate Goal Diff, Demo Diff, Shots Diff, and map Wins."""
    logging.info("Calculating diffs and mapping wins...")
    bs_df = pd.read_parquet("../data/parquet/better_team_stats.parquet")
    
    bs_df["Goal Diff"] = bs_df["Goals For"] - bs_df["Goals Against"]
    bs_df["Demo Diff"] = bs_df["Demos Inflicted"] - bs_df["Demos Taken"]
    bs_df["Shots Diff"] = bs_df["Shots For"] - bs_df["Shots Against"]
    
    team_stats_df = pd.read_parquet("../data/parquet/better_team_stats.parquet")
    team_wins = dict(zip(team_stats_df["Team"], team_stats_df["Wins"]))
    bs_df["Wins"] = bs_df["Team"].map(team_wins)
    
    logging.info("Diffs calculated and Wins mapped.")
    return bs_df

def calculate_weights_and_zscores(bs_df, team_opponents_stats):
    """Calculate weighted Z-scores and EPI Scores."""
    logging.info("Calculating weights and Z-scores...")
    win_perc_weight  = 0.6
    goal_diff_weight = 0.22
    shot_diff_weight = 0.06
    demo_diff_weight = 0.02
    strength_of_schedule = 0.10
    
    bs_df["Teams Played"] = bs_df["Team"].map(team_opponents_stats)
    teams_played_stats = pd.DataFrame(team_opponents_stats).T.reset_index().rename(columns={"index":"Team", "Win %": "Team Played Win %"})
    
    joint = bs_df.merge(teams_played_stats, on="Team")
    joint = joint.drop("Teams Played", axis=1)
    logging.debug("Merged Teams Played data.")
    
    joint[["Opponents Total Wins", "Opponents Total Games"]] = joint[["Opponents Total Wins", "Opponents Total Games"]].astype(int)
    joint["Team Played Win %"] = joint["Team Played Win %"].astype(float)
    
    # Calculate Z-scores with weights
    joint["Win % Zscore"] = zscore(joint["Win %"]) * win_perc_weight
    joint["Goal Diff Zscore"] = zscore(joint["Goal Diff"]) * goal_diff_weight
    joint["Demo Diff Zscore"] = zscore(joint["Demo Diff"]) * demo_diff_weight
    joint["Shots Diff Zscore"] = zscore(joint["Shots Diff"]) * shot_diff_weight
    joint["Team Played Win % Zscore"] = zscore(joint["Team Played Win %"]) * strength_of_schedule
    
    logging.debug("Calculated Z-scores with weights.")
    
    # Calculate EPI Score
    joint["EPI Score"] = joint[[
        "Win % Zscore", 
        "Goal Diff Zscore", 
        "Demo Diff Zscore", 
        "Shots Diff Zscore", 
        "Team Played Win % Zscore"
    ]].sum(axis=1)
    joint["EPI Rank"] = joint["EPI Score"].rank(ascending=False, method="min").astype(int)
    joint = joint.sort_values(by="EPI Rank", ascending=True)
    
    logging.info("EPI Scores and Ranks calculated.")
    
    final = joint[["Team", "EPI Score", "Games", "Win %", "Goals For", "Goals Against", 
                    "Goal Diff", "Shots For", "Shots Against", "Shots Diff", "Team Played Win %"]]
    final = final.rename(columns={"Team Played Win %":"Strength of Schedule"})
    final["EPI Score"] = round(final["EPI Score"] * 50, 2)
    final["Win %"] = final["Win %"].astype(int).apply(lambda x: f"{x}%" if x > 0 else str(x))
    
    logging.info("Final DataFrame with EPI Scores prepared.")
    return final

def save_final_data(final):
    """Save final DataFrame to Excel and export as an image."""
    logging.info("Saving final DataFrame to Excel and exporting as image...")
    excel_path = Path("../data/excel_files/final.xlsx")
    # final.set_index("Team").to_excel(excel_path)
    logging.info(f"Final DataFrame saved to {excel_path}")
    
    # Adjust metrics
    final["Goals For"] = round(final["Goals For"] / final["Games"], 2)
    final["Goals Against"] = round(final["Goals Against"] / final["Games"], 2)
    final["Shots For"] = round(final["Shots For"] / final["Games"], 2)
    final["Shots Against"] = round(final["Shots Against"] / final["Games"], 2)
    
    final["Goal Diff"] = final["Goal Diff"].apply(lambda x: f"+{x}" if int(x) > 0 else str(x))
    final["Shots Diff"] = final["Shots Diff"].apply(lambda x: f"+{x}" if int(x) > 0 else str(x))
    
    final = final.reset_index(drop=True)
    final.index = final.index + 1
    
    final = final.rename(columns={"Shots Diff":"Shot Diff"})
    
    final_parquet_path = Path("../data/parquet/final.parquet")
    final.to_parquet(final_parquet_path)
    logging.info(f"Final DataFrame saved to {final_parquet_path}")
    
    # Export to image using dataframe_image
    image_path = Path("images/table.png")
    dfi.export(final, image_path)
    logging.info(f"Final DataFrame image exported to {image_path}")

def process_player_data():
    """Process player data and export styled DataFrame as an image."""
    logging.info("Processing player data...")
    player_data_path = Path("../data/parquet/player_data.parquet")
    if not player_data_path.exists():
        logging.error(f"Player data file {player_data_path} does not exist.")
        raise FileNotFoundError(f"Player data file {player_data_path} does not exist.")
    
    df = pd.read_parquet(player_data_path)
    logging.info(f"Player data loaded from {player_data_path}")
    
    # Weights
    avg_score = 0.2
    goals_per_game = 0.3
    saves_per_game = 0.15
    assists_per_game = 0.19
    shots_per_game = 0.10
    demos_per_games = 0.05
    demos_taken_per_game = 0.05
    count_big_pads_stolen_per_game = 0.04
    count_small_pads_stolen_per_game = 0.02
    
    features_of_interest = ["name", "team", "game_average.core.score", "game_average.core.goals",
                            "game_average.core.assists", "game_average.core.saves",
                            "game_average.core.shots", "game_average.core.shooting_percentage",
                            "game_average.demo.inflicted", "game_average.demo.taken",
                            "game_average.boost.amount_stolen_big", "game_average.boost.amount_stolen_small"]
    
    df_filtered = df[features_of_interest]
    logging.debug("Selected features of interest from player data.")
    
    df_filtered.columns = ["Player", "Team", "Avg Score", "Goals Per Game", "Assists Per Game", 
                            "Saves Per Game", "Shots Per Game", "Shooting %", 
                            "Demos Inf. Per Game", "Demos Taken Per Game", 
                            "Big Boost Stolen", "Small Boost Stolen"]
    
    logging.debug("Renamed columns for clarity.")
    
    df_orig = df_filtered.copy()
    
    # Calculate Z-scores with weights
    logging.info("Calculating Z-scores and Dominance Quotient for players...")
    df_filtered["Avg Score Zscore"] = round(zscore(df_filtered["Avg Score"]) * avg_score, 2)
    df_filtered["Goals Per Game Zscore"] = round(zscore(df_filtered["Goals Per Game"]) * goals_per_game, 2)
    df_filtered["Assists Per Game Zscore"] = round(zscore(df_filtered["Assists Per Game"]) * assists_per_game, 2)
    df_filtered["Saves Per Game Zscore"] = round(zscore(df_filtered["Saves Per Game"]) * saves_per_game, 2)
    df_filtered["Shots Per Game Zscore"] = round(zscore(df_filtered["Shots Per Game"]) * shots_per_game, 2)
    df_filtered["Demos Inf. Per Game Zscore"] = round(zscore(df_filtered["Demos Inf. Per Game"]) * demos_per_games, 2)
    df_filtered["Demos Taken Per Game Zscore"] = round(zscore(df_filtered["Demos Taken Per Game"]) * demos_taken_per_game, 2)
    df_filtered["Big Boost Stolen Zscore"] = round(zscore(df_filtered["Big Boost Stolen"]) * count_big_pads_stolen_per_game, 2)
    df_filtered["Small Boost Stolen Zscore"] = round(zscore(df_filtered["Small Boost Stolen"]) * count_small_pads_stolen_per_game, 2)
    
    df_filtered["Shooting %"] = round(df_filtered["Shooting %"], 2)
    df_filtered["Shooting %"] = df_filtered["Shooting %"].apply(lambda x: f"{x}%")
    
    # Calculate Dominance Quotient
    dq_summation = [i for i in df_filtered.columns.tolist() if "Zscore" in i]
    df_filtered["Dominance Quotient"] = df_filtered[dq_summation].sum(axis=1) * 50
    
    # Calculate Roster Rating
    player_dq_summation = df_filtered.groupby("Team")["Dominance Quotient"].sum().reset_index()
    player_dq_summation_zipped = dict(zip(player_dq_summation["Team"], player_dq_summation["Dominance Quotient"]))
    df_filtered["Roster Rating"] = df_filtered["Team"].map(player_dq_summation_zipped)
    
    # Reorder columns
    new_order = ["Team", "Roster Rating"] + [col for col in df_filtered.columns.tolist() 
                                            if col not in ["Team", "EPI Score", "Roster Rating"]]
    df_filtered = df_filtered[new_order]
    logging.debug("Reordered columns for player DataFrame.")
    
    # Save team data to image
    team_data_path = Path("../data/parquet/final.parquet")
    if not team_data_path.exists():
        logging.error(f"Final team data file {team_data_path} does not exist.")
        raise FileNotFoundError(f"Final team data file {team_data_path} does not exist.")
    
    team_data = pd.read_parquet(team_data_path)
    logging.info(f"Team data loaded from {team_data_path}")
    
    team_data["Roster Rating"] = team_data["Team"].map(player_dq_summation_zipped)
    
    team_data_order = ["Team", "EPI Score", "Roster Rating", "Win %", "Goals For", 
                        "Goals Against", "Goal Diff", "Shots For", "Shots Against", 
                        "Shot Diff", "Strength of Schedule"]
    team_data = team_data[team_data_order]
    logging.debug("Reordered team data columns for styling.")
    
    team_df = team_data.style.format({
        'EPI Score': '{:.2f}', 
        'Roster Rating': '{:.2f}',         
        'Goals For': '{:.2f}',           
        'Goals Against': '{:.2f}',      
        'Shots For': '{:.2f}',           
        'Shots Against': '{:.2f}',       
        'Strength of Schedule': '{:.2f}' 
    }).set_table_styles([
        {'selector': 'thead th', 'props': 'color: #f8f8f2; background-color: #282a36;'},
        {'selector': 'tbody tr:nth-child(even) td, tbody tr:nth-child(even) th', 
            'props': 'background-color: #44475a; color: #f8f8f2;'},
        {'selector': 'tbody tr:nth-child(odd) td, tbody tr:nth-child(odd) th', 
            'props': 'background-color: #282a36; color: #f8f8f2;'},
        {'selector': 'td, th', 'props': 'border: none;'}
    ], overwrite=False)
    
    image2_path = Path("images/table2.png")
    image2_path.parent.mkdir(parents=True, exist_ok=True)
    dfi.export(team_df, image2_path)
    logging.info(f"Team DataFrame image exported to {image2_path}")
    
    # Prepare final player DataFrame
    final = df_filtered.drop(columns=dq_summation)
    
    for col in final.select_dtypes("number"):
        final[col] = final[col].round(2)
    
    new_order = ["Player", "Dominance Quotient"] + [col for col in final.columns.tolist() 
                                                    if col not in ["Player", "Dominance Quotient"]]
    final = final[new_order]
    final = final.sort_values(by="Dominance Quotient", ascending=False).reset_index(drop=True)
    final.index += 1
    
    actual_final = final.drop('Team', axis=1)
    
    # Ensure "Shooting %" is numeric
    actual_final['Shooting %'] = actual_final['Shooting %'].str.rstrip('%').astype('float') / 100
    
    actual_final = actual_final.drop(columns="Roster Rating", axis=1)
    
    # Calculate ranks for all numeric columns except "Player" and "Shooting %"
    ranked_df = actual_final.drop(columns=["Player", "Shooting %"]).rank(ascending=False).astype(int)
    
    def highlight_rank(s):
        if s.name in ["Player", "Dominance Quotient"]:
            return ['color: #f8f8f2;'] * len(s)
        
        # Reverse color scheme for "Demos Taken Per Game"
        if s.name == "Demos Taken Per Game":
            return ['color: lightcoral; font-weight: bold;' if v == s.max() else
                    'color: limegreen; font-weight: bold;' if v == s.min() else
                    'color: #f8f8f2;' for v in s]
        
        # Standard color scheme for all other columns
        return ['color: limegreen; font-weight: bold;' if v == s.max() else
                'color: lightcoral; font-weight: bold;' if v == s.min() else
                'color: #f8f8f2;' for v in s]
    
    # Apply styling
    styled_df = actual_final.style.apply(highlight_rank, subset=actual_final.columns)\
        .format({
            'Dominance Quotient': '{:.2f}', 
            'Avg Score': '{:.2f}',         
            'Goals Per Game': '{:.2f}',           
            'Assists Per Game': '{:.2f}',      
            'Saves Per Game': '{:.2f}',           
            'Shots Per Game': '{:.2f}',       
            'Shooting %': '{:.2%}',  # Convert back to percentage format
            'Demos Inf. Per Game': '{:.2f}',
            'Demos Taken Per Game': '{:.2f}',
            'Big Boost Stolen': '{:.2f}',
            'Small Boost Stolen': '{:.2f}'
        })\
        .set_properties(**{'text-align': 'center'})\
        .set_table_styles([
            {'selector': 'thead th', 'props': 'color: #f8f8f2; background-color: #282a36;'},
            {'selector': 'tbody tr:nth-child(even) td, tbody tr:nth-child(even) th', 
                'props': 'background-color: #44475a;'},
            {'selector': 'tbody tr:nth-child(odd) td, tbody tr:nth-child(odd) th', 
                'props': 'background-color: #282a36;'},
            {'selector': 'td, th', 'props': 'border: none; text-align: center;'},
            {'selector': '.row_heading, .blank', 'props': 'color: #f8f8f2; background-color: #282a36;'}
        ], overwrite=False)
    
    image_player_path = Path("images/player_data.png")
    image_player_path.parent.mkdir(parents=True, exist_ok=True)
    dfi.export(styled_df, image_player_path)
    logging.info(f"Player DataFrame image exported to {image_player_path}")

def main():
    """Main function to orchestrate data processing."""
    setup_logging()
    logging.info("Data processing pipeline started.")
    try:
        # Load environment variables
        TOKEN = load_environment()
        
        # Fetch and process replay data
        replay_df = fetch_replay_data(TOKEN)
        
        # Process blue and orange team data
        blue_df = process_team_players(replay_df, 'blue')
        orange_df = process_team_players(replay_df, 'orange')
        
        # Fetch and process group data
        logging.info("Fetching and processing group data...")
        replay_url = "https://ballchasing.com/api/groups/all-blcs-2-games-12x79igbdo"
        headers = {'Authorization': TOKEN}
        response = requests.get(replay_url, headers=headers)
        response.raise_for_status()
        logging.info(f"Group data fetched successfully with status code {response.status_code}.")
        json_data = response.json()
        df = pd.json_normalize(json_data, record_path=["players"])
        logging.debug("Normalized group data JSON into DataFrame.")
        df = df.sort_values(by="name")
        
        # Manual adjustments
        logging.info("Performing manual adjustments to specific rows...")
        df.loc[14, "cumulative.games"] -= 1
        df.loc[14, "cumulative.wins"] -= 1
        df.loc[14, "cumulative.win_percentage"] = df.loc[6, "cumulative.win_percentage"]
        df.loc[14, "cumulative.play_duration"] = df.loc[6, "cumulative.play_duration"]
        df.loc[14, "cumulative.core.shots_against"] = df.loc[6, "cumulative.core.shots_against"]
        df.loc[14, "game_average.core.goals_against"] = df.loc[6, "game_average.core.goals_against"]
        df.loc[14, "game_average.core.shots_against"] = df.loc[6, "game_average.core.shots_against"]
        
        df.loc[7, "cumulative.games"] -= 1
        df.loc[7, "cumulative.win_percentage"] = df.loc[2, "cumulative.win_percentage"]
        df.loc[7, "cumulative.play_duration"] = df.loc[2, "cumulative.play_duration"]
        df.loc[7, "cumulative.core.shots_against"] = df.loc[2, "cumulative.core.shots_against"]
        df.loc[7, "game_average.core.goals_against"] = df.loc[2, "game_average.core.goals_against"]
        df.loc[7, "game_average.core.shots_against"] = df.loc[2, "game_average.core.shots_against"]
        logging.info("Manual adjustments completed.")
        
        # Team dictionary
        team_dicts = {
            "BECKYARDIGANS": "BECKYARDIGANS",
            "KILLER": "KILLER B'S",
            "DIDDLERS":"DIDDLERS",
            "EXECUTIVE": "EXECUTIVE PROJEC",
            "MINORITIES":"MINORITIES",
            "PUSHIN":"PUSHIN PULLIS",
            "SCAVS":"SCAVS",
            "WONDER":"WONDER PETS"
        }
        logging.debug("Team dictionary defined.")
        
        # Aggregations
        logging.info("Performing aggregations on group data...")
        team_goals_df = df.groupby('team')["cumulative.core.goals"].sum().reset_index()
        team_goals_against = dict(zip(df["team"], df["cumulative.core.goals_against"]))
        team_goals = dict(zip(team_goals_df["team"], team_goals_df["cumulative.core.goals"]))
        
        demos_inflicted_df = df.groupby("team")["cumulative.demo.inflicted"].sum().reset_index()
        demos_taken_df = df.groupby("team")["cumulative.demo.taken"].sum().reset_index()
        
        demos_inflicted = dict(zip(demos_inflicted_df["team"], demos_inflicted_df["cumulative.demo.inflicted"]))
        demos_taken = dict(zip(demos_taken_df["team"], demos_taken_df["cumulative.demo.taken"]))
        
        shots_for_df = df.groupby("team")["cumulative.core.shots"].sum().reset_index()
        shots_against_df = df.groupby('team')["cumulative.core.shots_against"].sum().reset_index()
        
        shots_for = dict(zip(shots_for_df["team"], shots_for_df["cumulative.core.shots"]))
        shots_against = dict(zip(df["team"], df["cumulative.core.shots_against"]))
        
        final_df = pd.DataFrame(df["team"].unique(), columns=["Team"])
        
        final_df["Win %"] = final_df["Team"].map(dict(zip(df["team"], df["cumulative.win_percentage"])))
        final_df["Games"] = final_df["Team"].map(dict(zip(df["team"], df["cumulative.games"])))
        final_df["Wins"] = final_df["Team"].map(dict(zip(df["team"], df["cumulative.wins"])))
        final_df["Goals For"] = final_df["Team"].map(team_goals)
        final_df["Goals Against"] = final_df["Team"].map(team_goals_against)
        final_df["Shots For"] = final_df["Team"].map(shots_for)
        final_df["Shots Against"] = final_df["Team"].map(shots_against)
        final_df["Demos Inflicted"] = final_df["Team"].map(demos_inflicted)
        final_df["Demos Taken"] = final_df["Team"].map(demos_taken)
        
        df["team"] = df["team"].str.replace("'", "", regex=True)
        
        os.makedirs("../data/excel_files", exist_ok=True)
        final_df.to_parquet("../data/parquet/better_team_stats.parquet")
        df.to_parquet("../data/parquet/player_data.parquet")
        logging.info("Team and player data saved to Parquet files.")
        
        # Process diffs and wins
        bs_df = calculate_diffs_and_wins()
        
        # Create team opponents mapping
        logging.info("Creating team opponents mapping...")
        team_opponents = {}
        for _, row in replay_df.iterrows():
            blue_team = row["blue.name"]
            orange_team = row["orange.name"]
    
            if blue_team not in team_opponents:
                team_opponents[blue_team] = []
            if orange_team not in team_opponents[blue_team]:
                team_opponents[blue_team].append(orange_team)
    
            if orange_team not in team_opponents:
                team_opponents[orange_team] = []
            if blue_team not in team_opponents[orange_team]:
                team_opponents[orange_team].append(blue_team)
        logging.info("Team opponents mapping created.")
    
        team_stats_dict = bs_df.set_index("Team").T.to_dict()
        team_opponents_stats = {}
    
        for team, opponents in team_opponents.items():
            total_wins = 0
            total_games = 0
    
            for opponent in opponents:
                opponent_stats = team_stats_dict.get(opponent, {"Wins": 0, "Games" : 0})
                total_wins += opponent_stats["Wins"]
                total_games += opponent_stats["Games"]
    
            win_percentage = round(float(total_wins / total_games), 2) if total_games > 0 else 0.0
            team_opponents_stats[team] = {
                'Opponents': opponents,
                "Opponents Total Wins": int(total_wins),
                "Opponents Total Games": int(total_games),
                "Win %": win_percentage,
            }
        logging.info("Calculated opponents' win percentages.")
    
        # Calculate weights and Z-scores
        final = calculate_weights_and_zscores(bs_df, team_opponents_stats)
        
        # Save final data
        save_final_data(final)
        
        # Process player data
        process_player_data()
        
        logging.info("Data processing pipeline completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred during data processing: {e}")
        raise

if __name__ == "__main__":
    main()
