# tests/test_bot.py
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from discord.ext import commands
from discord import Interaction, File
from database.database import Database
from discord_bot.cogs.slash_commands import SlashCommands
import pandas as pd

class TestSlashCommands(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = commands.Bot(command_prefix="!")
        self.cog = SlashCommands(self.bot)
        self.interaction = MagicMock(spec=Interaction)
        self.interaction.response = MagicMock()

    async def test_draft_odds_command_with_data(self):
        # Mock the database response
        self.cog.db.fetch_teams = MagicMock(return_value=[
            {'name': 'Team A', 'EPI_Score': 90.0},
            {'name': 'Team B', 'EPI_Score': 85.5}
        ])
        await self.cog.draft_odds(self.interaction)
        self.interaction.response.send_message.assert_called_once()
        args, kwargs = self.interaction.response.send_message.call_args
        self.assertIn("Draft Odds for Next Season", args[0])

    async def test_draft_odds_command_no_data(self):
        # Mock the database response
        self.cog.db.fetch_teams = MagicMock(return_value=[])
        await self.cog.draft_odds(self.interaction)
        self.interaction.response.send_message.assert_called_once_with(
            "No teams found in the database.", ephemeral=True
        )

    async def test_predict_command_player_found(self):
        # Mock the database response
        self.cog.db.fetch_player_stats = MagicMock(return_value={
            'name': 'Player1',
            'points': 25.3,
            'assists': 5.2,
            'rebounds': 4.1,
            'steals': 1.2,
            'blocks': 0.8
        })
        # Mock visualization functions
        with patch('discord_bot.cogs.slash_commands.create_radar_chart', return_value=b'radar_image_bytes'), \
             patch('discord_bot.cogs.slash_commands.create_kpi_panel', return_value=b'kpi_image_bytes'):
            await self.cog.predict(self.interaction, "Player1")
            self.interaction.response.send_message.assert_called_once()
            args, kwargs = self.interaction.response.send_message.call_args
            self.assertIn("Prediction for Player1", args[0])
            self.assertIn('files', kwargs)
            self.assertEqual(len(kwargs['files']), 2)

    async def test_predict_command_player_not_found(self):
        # Mock the database response
        self.cog.db.fetch_player_stats = MagicMock(return_value=None)
        await self.cog.predict(self.interaction, "UnknownPlayer")
        self.interaction.response.send_message.assert_called_once_with(
            "Player 'UnknownPlayer' not found.", ephemeral=True
        )

    async def test_team_stats_command_with_data(self):
        # Mock the database response
        self.cog.db.fetch_teams_dataframe = MagicMock(return_value=pd.DataFrame([
            {'Team': 'Team A', 'EPI Score': 4500.00, 'Games': 20, 'Win %': '80%', 
             'Goals For': 100.0, 'Goals Against': 80.0, 'Goal Diff': 20.0,
             'Shots For': 300.0, 'Shots Against': 250.0, 'Shots Diff': 50.0, 
             'Strength of Schedule': 1.20, 'Differential': 20.0, 'Dominance Quotient': 1.20}
        ]))
        # Mock visualization function
        with patch('discord_bot.cogs.slash_commands.create_team_table_image', return_value=b'team_table_image_bytes'):
            await self.cog.team_stats(self.interaction)
            self.interaction.response.send_message.assert_called_once()
            args, kwargs = self.interaction.response.send_message.call_args
            self.assertIn("Current Team Stats:", args[0])
            self.assertIn('file', kwargs)
            self.assertIsInstance(kwargs['file'], File)

    async def test_team_stats_command_no_data(self):
        # Mock the database response
        self.cog.db.fetch_teams_dataframe = MagicMock(return_value=pd.DataFrame())
        await self.cog.team_stats(self.interaction)
        self.interaction.response.send_message.assert_called_once_with(
            "No team stats available.", ephemeral=True
        )

    async def asyncTearDown(self):
        self.cog.db.close()

if __name__ == '__main__':
    unittest.main()
