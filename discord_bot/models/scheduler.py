# models/scheduler.py
from datetime import datetime, timedelta
from models.player import Player
from models.team import Team

class Scheduler:
    @staticmethod
    async def find_match_times(team1: str, team2: str, date: datetime.date):
        team1_players = await Team.get_players(team1)
        team2_players = await Team.get_players(team2)

        all_players = team1_players + team2_players
        availabilities = []

        for player_id in all_players:
            player_avail = await Player.get_availability(player_id)
            day_avail = player_avail.get(date.strftime("%A"), [])
            availabilities.extend(day_avail)

        if not availabilities:
            return []

        # Find overlapping time slots
        start_times = sorted(set(slot["start"] for slot in availabilities))
        end_times = sorted(set(slot["end"] for slot in availabilities))

        possible_slots = []
        for start in start_times:
            for end in end_times:
                if end > start:
                    if all(self.time_in_slot(start, end, slot) for slot in availabilities):
                        possible_slots.append({"start": start, "end": end})

        return possible_slots

    @staticmethod
    def time_in_slot(start: str, end: str, slot: dict):
        return slot["start"] <= start and slot["end"] >= end
