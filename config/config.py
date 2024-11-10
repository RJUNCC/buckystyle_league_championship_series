# config/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

class Config:
    BALLCHASING_TOKEN = os.getenv("TOKEN")
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    DJANGO_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE")
