class League:
    def __init__(self):
        self.series_count = 2  # Default to 1 series per matchup
        self.games_per_series = 5  # Best of 5

    def set_series_count(self, count):
        self.series_count = count

    def get_series_info(self):
        return {
            "series_count": self.series_count,
            "games_per_series": self.games_per_series,
            "win_condition": (self.games_per_series // 2) + 1
        }