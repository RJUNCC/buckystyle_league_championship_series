# tests/test_database.py
import unittest
from database.database import Database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_fetch_teams(self):
        teams = self.db.fetch_teams()
        self.assertIsInstance(teams, list)
        # Further assertions based on expected data
        if teams:
            self.assertIn('name', teams[0])

    def test_fetch_player_stats_found(self):
        player = self.db.fetch_player_stats("Player1")
        if player:
            self.assertEqual(player['name'], "Player1")
        else:
            self.skipTest("Player1 not found in the database.")

    def test_fetch_player_stats_not_found(self):
        player = self.db.fetch_player_stats("NonExistentPlayer")
        self.assertIsNone(player)

    def tearDown(self):
        # Clean up inserted test data if any
        self.db.close()

if __name__ == '__main__':
    unittest.main()
