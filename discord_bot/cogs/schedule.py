import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
from collections import defaultdict

TOKEN = 'YOUR_BOT_TOKEN'

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Store availability and match data
player_availability = defaultdict(dict)  # {player_id: {day: [time1, time2, ...]}}
team_last_played = defaultdict(datetime)  # {team_id: last_played_time}
matches = []  # To track scheduled matches

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    weekly_prompt.start()
    daily_reminder.start()

@tasks.loop(weeks=1)
async def weekly_prompt():
    """Prompt players weekly to enter their availability."""
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                try:
                    await member.send(
                        "Please provide your availability for this week in the format `Day HH:MM AM/PM`. Example: `Monday 3:00 PM`. You can send multiple messages."
                    )
                except discord.Forbidden:
                    print(f"Could not DM {member.name}")

@tasks.loop(hours=24)
async def daily_reminder():
    """Remind players daily if they haven't entered availability."""
    now = datetime.now()
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot and member.id not in player_availability:
                try:
                    await member.send(
                        "Hi! We noticed you haven't entered your availability for this week. Please send your times in the format `Day HH:MM AM/PM`."
                    )
                except discord.Forbidden:
                    print(f"Could not DM {member.name}")

@bot.event
async def on_message(message):
    """Collect player availability."""
    if message.author.bot:
        return

    try:
        # Parse day and time from the message
        content = message.content.strip()
        day, time = content.split(" ", 1)
        player_availability[message.author.id][day] = player_availability[message.author.id].get(day, []) + [time]
        await message.channel.send(f"Thanks, {message.author.mention}! Your availability has been recorded.")
    except ValueError:
        pass  # Ignore messages that don't match the expected format

async def find_and_schedule_matches():
    """Match teams and schedule games based on availability."""
    for team1, team2 in team_combinations():
        # Check cooldowns
        now = datetime.now()
        if (team1 in team_last_played and now - team_last_played[team1] < timedelta(minutes=30)) or \
           (team2 in team_last_played and now - team_last_played[team2] < timedelta(minutes=30)):
            continue

        # Find overlapping availability
        overlap = find_overlap(team1, team2)
        if overlap:
            day, time = overlap
            # Schedule the match
            matches.append((team1, team2, day, time))
            team_last_played[team1] = now
            team_last_played[team2] = now
            await create_match_channel(team1, team2, day, time)
            break  # Avoid scheduling multiple matches at once

async def create_match_channel(team1, team2, day, time):
    """Create a channel for the match and notify players."""
    guild = bot.guilds[0]  # Assuming one guild
    match_channel = await guild.create_text_channel(f"match-{team1}-{team2}")
    await match_channel.send(
        f"Match scheduled between Team {team1} and Team {team2} on {day} at {time}. Good luck!"
    )

def team_combinations():
    """Generate team combinations (replace with actual team data)."""
    teams = ["Team A", "Team B", "Team C", "Team D"]  # Example teams
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            yield teams[i], teams[j]

def find_overlap(team1, team2):
    """Find overlapping availability for two teams."""
    team1_players = [1, 2, 3]  # Replace with actual player IDs
    team2_players = [4, 5, 6]

    team1_availability = get_combined_availability(team1_players)
    team2_availability = get_combined_availability(team2_players)

    for day, times in team1_availability.items():
        if day in team2_availability:
            for time in times:
                if time in team2_availability[day]:
                    return day, time
    return None

def get_combined_availability(players):
    """Combine availability for a list of players."""
    combined = defaultdict(list)
    for player in players:
        if player in player_availability:
            for day, times in player_availability[player].items():
                combined[day].extend(times)
    return combined

# Run the bot
bot.run(TOKEN)
