import os
import sys
import traceback
import yaml

print("=== APP STARTING ===")
print(f"Python version: {sys.version}")

try:
    import pandas as pd
    from sqlalchemy import create_engine
    from taipy.gui import Gui, Markdown
    from dotenv import load_dotenv
    from pathlib import Path
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# --- Path setup for Docker ---
PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "shared" / "config" / "conf"

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"CONFIG_PATH: {CONFIG_PATH}")

# Load config manually instead of using Hydra
def load_config():
    """Load configuration from YAML file manually."""
    config_file = CONFIG_PATH / "dashboard_config.yaml"
    print(f"Loading config from: {config_file}")
    
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✅ Config loaded: {config}")
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

# --- Database Connection ---
def get_database_url():
    """Gets the database URL from environment variables."""
    db_url = os.getenv('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    return db_url

def get_data_from_db(config):
    """Fetches player statistics from the database using a JOIN."""
    db_url = get_database_url()
    if not db_url:
        print("DATABASE_URL environment variable not set.")
        return pd.DataFrame()

    try:
        engine = create_engine(db_url)
        stats_table = config['stats_table_name']
        player_mappings = config['player_mapping_table_name']
        columns = ", ".join([f"{col}" for col in config['columns']])
        print(f"Columns: {columns}")
        
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

def create_app(config):
    """Create and return the Taipy app with all variables in proper scope."""
    print("=== CREATE APP STARTING ===")
    
    # Load environment variables from .env file (if it exists)
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    # Fetch initial data
    initial_data = get_data_from_db(config)
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

    print("=== CREATE APP COMPLETED ===")
    # Create the GUI with all variables in local scope
    return Gui(page=Markdown(page)), {
        'initial_data': initial_data,
        'player_data': player_data,
        'player_list': player_list,
        'selected_player': selected_player,
        'on_change_player': on_change_player
    }

def main():
    """Main function to set up and run the Taipy GUI."""
    
    print("=== MAIN FUNCTION STARTING ===")
    
    # DEBUG: Print environment info
    print("=== ENVIRONMENT DEBUG ===")
    print(f"PORT: {os.environ.get('PORT', 'NOT SET')}")
    print(f"DATABASE_URL: {'SET' if os.environ.get('DATABASE_URL') else 'NOT SET'}")
    
    try:
        print("=== LOADING CONFIG ===")
        config = load_config()
        if not config:
            print("❌ Failed to load config")
            sys.exit(1)
            
        print("=== CREATING APP ===")
        gui, context = create_app(config)
        
        # CRITICAL FIX: Force host to 0.0.0.0
        port = int(os.environ.get('PORT', 8080))
        host = '0.0.0.0'  # This MUST be 0.0.0.0, not localhost
        
        print(f"=== STARTING SERVER ===")
        print(f"Host: {host}")
        print(f"Port: {port}")
        
        # Run the GUI with the context variables
        gui.run(
            title="BLCS Player Dashboard",
            host=host,  # CRITICAL: This must be 0.0.0.0
            port=port,
            debug=False,
            **context
        )
    except Exception as e:
        print(f"❌ ERROR in main function: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    print("=== SCRIPT STARTING ===")
    try:
        main()
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        sys.exit(1)