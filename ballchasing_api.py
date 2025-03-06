# ballchasing_api.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class BallchasingAPI:
    BASE_URL = "https://ballchasing.com/api"
    TOKEN = os.getenv("TOKEN")
    CURRENT_GROUP_ID = os.getenv("CURRENT_GROUP_ID")

    @classmethod
    def get_group_data(cls):
        url = f"{cls.BASE_URL}/groups/{cls.CURRENT_GROUP_ID}"
        headers = {"Authorization": cls.TOKEN}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    @classmethod
    def get_player_data(cls):
        data = cls.get_group_data()
        return data.get("players", [])

    @classmethod
    def get_team_data(cls):
        data = cls.get_group_data()
        return data.get("teams", [])
