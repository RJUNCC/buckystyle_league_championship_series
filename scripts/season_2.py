import requests
import pandas as pd
from pathlib import Path
import logging
import os
import sys
from scipy.stats import zscore
import dataframe_image as dfi

current_dir = os.path.dirname(os.path.abspath("__file__"))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from config.config import Config
from visualization.visualization import make_highlighted_table, team_styled_table

config = Config()

def overall_stats():
    """
    This function retrieves and merges playoff and regular season data.
    """
    # load data
    playoff_player_data = pd.read_parquet(f"../data/parquet/{config.playoff_player_data}")
    regular_player_data = pd.read_parquet(f"../data/parquet/{config.regular_player_data}")
    playoff_player_data = playoff_player_data.sort_values(by=['Dominance Quotient'], ascending=False).reset_index(drop=True)
    playoff_player_data.loc[9, "Player"] = ".Xero"
    

    # add playoff and regular prefixes
    playoff_player_data = playoff_player_data.add_prefix("playoff_")
    regular_player_data = regular_player_data.add_prefix("regular_")

    # merge data
    player_data = pd.merge(
        playoff_player_data,
        regular_player_data,
        left_on="playoff_Player",
        right_on="regular_Player",
        how="outer"
    )

    player_data["playoff_Dominance Quotient"] = player_data["playoff_Dominance Quotient"] * 0.6
    player_data["regular_Dominance Quotient"] = player_data["regular_Dominance Quotient"] * 0.4
    player_data["Total Dominance Quotient"] = player_data["playoff_Dominance Quotient"] + player_data["regular_Dominance Quotient"]

    final = player_data.sort_values(by=["Total Dominance Quotient"], ascending=False).reset_index(drop=True)
    final = final.drop(["regular_Player", "playoff_Dominance Quotient", "regular_Dominance Quotient"], axis=1)
    final = final.rename(columns={"playoff_Player": "Player"})
    final = final[["Player", "Total Dominance Quotient"] + [col for col in final.columns if col not in ["Player", "Total Dominance Quotient"]]] 
    final.index += 1

    final.to_parquet(f"../data/parquet/{config.overall_player_data}")
    
    return final

def team_styled_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    # List of numerical columns to format
    numerical_columns = [
        'Total Dominance Quotient', 'playoff_Avg Score', 'playoff_Goals Per Game', 
        'playoff_Assists Per Game', 'playoff_Saves Per Game', 'playoff_Shots Per Game', 
        'playoff_Shooting %', 'playoff_Demos Inf. Per Game', 'playoff_Demos Taken Per Game', 
        'playoff_Big Boost Stolen', 'playoff_Small Boost Stolen', 'regular_Avg Score', 
        'regular_Goals Per Game', 'regular_Assists Per Game', 'regular_Saves Per Game', 
        'regular_Shots Per Game', 'regular_Shooting %', 'regular_Demos Inf. Per Game', 
        'regular_Demos Taken Per Game', 'regular_Big Boost Stolen', 'regular_Small Boost Stolen'
    ]
    
    # Dynamically filter numerical columns excluding 'Player'
    columns_to_format = [col for col in numerical_columns if col in df.columns and col != 'Player']
    
    # Apply formatting dynamically
    team_df = df.style.format({col: '{:.2f}' for col in columns_to_format}).set_table_styles([
        {'selector': 'thead th', 'props': 'color: #f8f8f2; background-color: #282a36;'},
        {'selector': 'tbody tr:nth-child(even) td, tbody tr:nth-child(even) th', 
            'props': 'background-color: #44475a; color: #f8f8f2;'},
        {'selector': 'tbody tr:nth-child(odd) td, tbody tr:nth-child(odd) th', 
            'props': 'background-color: #282a36; color: #f8f8f2;'},
        {'selector': 'td, th', 'props': 'border: none;'}
    ], overwrite=False)
    
    return team_df

def main():
    overall_player_data = overall_stats()
    team_styled_df = team_styled_table(overall_player_data)
    dfi.export(team_styled_df, f"../images/season_2_overall_player_data.png")

if __name__ == "__main__":
    main()