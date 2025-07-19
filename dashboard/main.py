import os
import pandas as pd
from sqlalchemy import create_engine
from taipy.gui import Gui, Markdown
import hydra
from omegaconf import DictConfig
from dotenv import load_dotenv
from pathlib import Path

# --- Path setup for Docker ---
# In Docker, the working directory is /app, and shared is copied to /app/shared
PROJECT_ROOT = Path(__file__).resolve().parent  # /app
CONFIG_PATH = PROJECT_ROOT / "shared" / "config" / "conf"

# --- Database Connection ---
def get_database_url():
    """Gets the database URL from environment variables."""
    db_url = os.getenv('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    return db_url

def get_data_from_db(cfg: DictConfig):
    """Fetches player statistics from the database using a JOIN."""
    db_url = get_database_url()
    if not db_url:
        print("DATABASE_URL environment variable not set.")
        return pd.DataFrame()

    try:
        engine = create_engine(db_url)
        stats_table = cfg.stats_table_name
        player_mappings = cfg.player_mapping_table_name
        columns = ", ".join([f"{col}" for col in cfg.columns])
        print(columns)
        
        query = f"""
        SELECT
            {columns}
        FROM {stats_table} s
        JOIN {player_mappings} p 
        ON s.player_id = p.ballchasing_player_id
        """
        df = pd.read_sql(query, engine)
        print(f"Successfully fetched {len(df)} rows from the database.")
        
        # Ensure discord_username is string type and handle potential None values
        df['discord_username'] = df['discord_username'].astype(str)
        
        # Extract just the player name (before the " | ") using regex
        df['player_name'] = df['discord_username'].str.extract(r'^([^|]+)').iloc[:, 0].str.strip()
        
        # Extract the team name (after the " | ") using regex
        df['team_name'] = df['discord_username'].str.extract(r'\|\s*(.+)$').iloc[:, 0].str.strip()
        
        return df
    except Exception as e:
        print(f"Error fetching data from database: {e}")
        return pd.DataFrame()

def create_app(cfg: DictConfig):
    """Create and return the Taipy app with all variables in proper scope."""
    # Load environment variables from .env file (if it exists)
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Fetch initial data
    initial_data = get_data_from_db(cfg)
    player_data = initial_data.copy()
    
    # Populate the player list for the dropdown using cleaned names
    player_list = ["All"]
    if not player_data.empty and 'player_name' in player_data.columns:
        # Get unique player names (cleaned) and sort them
        unique_players = sorted(player_data["player_name"].dropna().unique().tolist())
        player_list.extend(unique_players)
    
    print("Player list:", player_list)
    
    selected_player = "All"

    # --- Taipy Callbacks ---
    def on_change_player(state):
        """Callback to update data based on selected player."""
        if state.selected_player == "All":
            state.player_data = initial_data
        else:
            # Filter by the cleaned player name
            state.player_data = initial_data[initial_data["player_name"] == state.selected_player]

    # --- Taipy Page Definition ---
    page = """
# BuckyStyle League Championship Series - Player Stats

<|{selected_player}|selector|lov={player_list}|on_change=on_change_player|dropdown=true|label=Select a Player|>

<|{player_data}|table|width=100%|>

<|{player_data}|chart|type=bar|x=player_name|y[1]=goals_per_game|y[2]=assists_per_game|y[3]=saves_per_game|y[4]=shots_per_game|>
"""

    # Create the GUI with all variables in local scope
    return Gui(page=Markdown(page)), {
        'initial_data': initial_data,
        'player_data': player_data,
        'player_list': player_list,
        'selected_player': selected_player,
        'on_change_player': on_change_player
    }

@hydra.main(version_base=None, config_path="shared/config/conf", config_name="dashboard_config")
def main(cfg: DictConfig):
    """Main function to set up and run the Taipy GUI."""
    gui, context = create_app(cfg)
    
    # Production settings for DigitalOcean
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'
    
    # Run the GUI with the context variables
    gui.run(
        title="BLCS Player Dashboard",
        host=host,
        port=port,
        debug=False,
        **context
    )

if __name__ == "__main__":
    main()