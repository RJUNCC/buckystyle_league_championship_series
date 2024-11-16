# models/team_metrics/metrics_calculator.py
import pandas as pd
from database.database import Database
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_additional_metrics():
    logging.info("Calculating additional team metrics...")

    db = Database()
    teams_df = db.fetch_teams_dataframe()
    db.close()

    if teams_df.empty:
        logger.warning("No team data available to calculate additional metrics.")
        return

    # Example: Dominance Quotient already calculated in data_processing.py
    # Add more metrics as needed
    teams_df['Efficiency'] = teams_df['Goals For'] / (teams_df['Shots For'] + 1)  # Avoid division by zero
    teams_df['Offensive Rating'] = teams_df['Goals For'] / teams_df['Games']
    teams_df['Defensive Rating'] = teams_df['Goals Against'] / teams_df['Games']

    # Insert or update metrics back into the database
    db = Database()
    for _, row in teams_df.iterrows():
        team_data = (
            row["Team"],
            row["EPI Score"],
            row["EPI Rank"],
            row["Games"],
            row["Win %"],
            row["Goals For"],
            row["Goals Against"],
            row["Goal Diff"],
            row["Shots For"],
            row["Shots Against"],
            row["Shots Diff"],
            row["Strength of Schedule"],
            row["Dominance Quotient"],
            row["Differential"],
            row["Efficiency"],
            row["Offensive Rating"],
            row["Defensive Rating"]
        )
        db.insert_team(team_data)  # Adjust the insert_team method to handle new metrics if necessary
    db.close()

    logging.info("Additional team metrics calculated and updated in the database.")

def main():
    try:
        calculate_additional_metrics()
        logging.info("Additional metrics calculation completed successfully.")
    except Exception as e:
        logging.error(f"An error occurred during metrics calculation: {e}")

if __name__ == "__main__":
    main()
