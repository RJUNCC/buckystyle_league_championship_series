# tests/test_bot.py
import unittest
from unittest.mock import MagicMock
from discord_bot.bot import bot

class TestDiscordBot(unittest.TestCase):
    def test_bot_ready(self):
        mock_user = MagicMock()
        mock_user.name = "TestBot"
        with self.assertLogs(level='INFO') as log:
            bot.on_ready()
            self.assertIn("Logged in as TestBot", log.output[0])

if __name__ == '__main__':
    unittest.main()
