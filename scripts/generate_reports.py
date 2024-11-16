# scripts/generate_reports.py

import pandas as pd
import logging
from database.database import Database
from pathlib import Path
import sys
import traceback

def setup_logging():
    """Configure logging for the script."""
    log_dir = Path("../logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "generate_reports.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)  # Also log to console
        ]
    )

def generate_team_report():
    """Generate a team report and save it as an Excel file."""
    logger = logging.getLogger(__name__)
    logger.info("Starting team report generation.")
    
    db = None
    try:
        db = Database()
        teams_df = db.fetch_teams_dataframe()
        logger.info("Fetched team data from the database.")
        
        if teams_df.empty:
            logger.warning("No team data available to generate report.")
            return
        
        # Define the path for the report
        reports_dir = Path("../data/excel_files")
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / "team_report.xlsx"
        
        # Save DataFrame to Excel
        teams_df.to_excel(report_path, index=False)
        logger.info(f"Team report generated successfully at {report_path}.")
        
    except Exception as e:
        logger.error(f"An error occurred while generating the team report: {e}")
        logger.debug(traceback.format_exc())
    finally:
        if db:
            db.close()
            logger.info("Database connection closed after team report generation.")

def generate_player_report():
    """Generate a player report and save it as an Excel file."""
    logger = logging.getLogger(__name__)
    logger.info("Starting player report generation.")
    
    db = None
    try:
        db = Database()
        query = "SELECT * FROM players;"
        db.cursor.execute(query)
        players = db.cursor.fetchall()
        players_df = pd.DataFrame(players)
        logger.info("Fetched player data from the database.")
        
        if players_df.empty:
            logger.warning("No player data available to generate report.")
            return
        
        # Define the path for the report
        reports_dir = Path("../data/excel_files")
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / "player_report.xlsx"
        
        # Save DataFrame to Excel
        players_df.to_excel(report_path, index=False)
        logger.info(f"Player report generated successfully at {report_path}.")
        
    except Exception as e:
        logger.error(f"An error occurred while generating the player report: {e}")
        logger.debug(traceback.format_exc())
    finally:
        if db:
            db.close()
            logger.info("Database connection closed after player report generation.")

def main():
    """Main function to orchestrate report generation."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Report generation process started.")
    
    try:
        generate_team_report()
        generate_player_report()
        logger.info("All reports generated successfully.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during report generation: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
