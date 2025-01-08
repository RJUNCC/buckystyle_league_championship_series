# config/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    def __init__(self):
        # Private attributes
        # self._database_name = os.getenv("DATABASE_NAME")
        # self._database_user = os.getenv("DATABASE_USER")
        # self._database_password = os.getenv("DATABASE_PASSWORD")
        # self._database_host = os.getenv("DATABASE_HOST")
        # self._database_port = os.getenv("DATABASE_PORT")
        # self._database_url  = os.getenv("DATABASE_URL")
        self._ballchasing_token = os.getenv("TOKEN")
        self._playoff_group_url = os.getenv("PLAYOFF_GROUP_URL")
        self.current_group_id   = os.getenv("CURRENT_GROUP_ID")
        self._player_channel_id = os.getenv("PLAYER_CHANNEL_ID")
        self._team_channel_id   = os.getenv("TEAM_CHANNEL_ID")
        self._worlds_group_id   = "1-swiss-stage-4ws5jld17r"

        # Discord Configs
        self._discord_token = os.getenv("DISCORD_TOKEN")
        self.channel_id3 = os.getenv("CHANNEL_ID3")

        # Weights for player data
        self.avg_score = 0.2
        self.goals_per_game = 0.3
        self.saves_per_game = 0.15
        self.assists_per_game = 0.19
        self.shots_per_game = 0.10
        self.demos_per_games = 0.05
        self.demos_taken_per_game = -0.05
        self.count_big_pads_stolen_per_game = 0.04
        self.count_small_pads_stolen_per_game = 0.02

        # Weights for team data
        self.win_perc_weight  = 0.6
        self.goal_diff_weight = 0.22
        self.shot_diff_weight = 0.06
        self.demo_diff_weight = 0.02
        self.strength_of_schedule = 0.10

        # Fantasy Points
        self.goals_pts = 5.0
        self.assists_pts = 2.0
        self.saves_pts = 3.0
        self.shots_pts = 1.0
        self.demos_inf_pts = 0.5
        self.demos_taken_pts = -0.5

        # Dominance Quotient
        self.dominance_quotient_multiplier = 20

        # File for data
        self.playoff_player_data = "playoff_player_data_season_2.parquet"
        self.playoff_team_data = "playoff_team_data_season_2.parquet"
        self.regular_player_data = "season_2_player_stats.parquet"
        self.regular_team_data = "season_2_team_stats.parquet"
        self.overall_player_data = "season_3_overall_player_data.parquet"

        self.all_player_data = "season_3_player_data"
        self.all_team_data = "season_3_team_data"

        # PATHS TO GROUPS
        self.all_blcs_season_2_matches_link = "all-blcs-2-matches-reg-playoffs-ajmebwvz3b"

        
        # # Validate that all required environment variables are set
        # missing_vars = []
        # if not self._database_name:
        #     missing_vars.append("DATABASE_NAME")
        # if not self._database_user:
        #     missing_vars.append("DATABASE_USER")
        # if not self._database_password:
        #     missing_vars.append("DATABASE_PASSWORD")
        # if not self._database_host:
        #     missing_vars.append("DATABASE_HOST")
        # if not self._database_port:
        #     missing_vars.append("DATABASE_PORT")
        
        # if missing_vars:
        #     raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # # Properties to access the private attributes
    # @property
    # def database_name(self):
    #     return self._database_name

    # @property
    # def database_user(self):
    #     return self._database_user

    # @property
    # def database_password(self):
    #     return self._database_password

    # @property
    # def database_host(self):
    #     return self._database_host

    # @property
    # def database_port(self):
    #     return self._database_port
