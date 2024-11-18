# cogs/commands.py
from discord.ext import commands
from discord import File
from config.config import Config
import pandas as pd
import io
import logging

# Import visualization functions
from visualization import create_radar_chart, create_draft_odds_table

class Commands(commands.Cog):
    def __init__(self, bot, config: Config):
        self.bot = bot
        self.config = config
        # Load data
        self.final_df = pd.read_parquet("../data/parquet/final.parquet")
        self.final_player_df = pd.read_parquet("../data/parquet/final_player_data.parquet")

    @commands.slash_command(name='predict', description='Get prediction and stats for a player.')
    async def predict(self, ctx, player_name: str):
        """Generate and send a radar chart and KPI panel for a specified player."""
        await ctx.defer()  # Acknowledge the command to allow more time for processing

        try:
            player = self.final_player_df[self.final_player_df["Player"].str.lower() == player_name.lower()]
            if player.empty:
                await ctx.respond(f"Player '{player_name}' not found.", ephemeral=True)
                logging.warning(f"Player '{player_name}' not found by {ctx.author} in channel {ctx.channel.id}")
                return

            player = player.iloc[0]

            # Generate radar chart and KPI panel
            radar_img = create_radar_chart(player)
            kpi_img = create_kpi_panel(player)

            # Create BytesIO objects
            radar_bytes = io.BytesIO(radar_img)
            kpi_bytes = io.BytesIO(kpi_img)

            # Create File objects
            radar_file = File(fp=radar_bytes, filename=f"{player['Player']}_radar.png")
            kpi_file = File(fp=kpi_bytes, filename=f"{player['Player']}_kpi.png")

            # Send files
            await ctx.respond(
                content=f"**Prediction for {player['Player']}**",
                files=[radar_file, kpi_file]
            )
            logging.info(f"Sent predictions for player '{player['Player']}' to {ctx.author} in channel {ctx.channel.id}")

        except Exception as e:
            await ctx.respond("An error occurred while generating predictions.", ephemeral=True)
            logging.error(f"Error in predict command: {e}")

    @commands.slash_command(name='draft_odds', description='Get draft odds for teams.')
    async def draft_odds(self, ctx):
        """Generate and send a draft odds table."""
        await ctx.defer()  # Acknowledge the command to allow more time for processing

        try:
            # Generate draft odds table image
            draft_odds_img = create_draft_odds_table(self.final_df)

            # Create BytesIO object
            draft_odds_bytes = io.BytesIO(draft_odds_img)

            # Create File object
            draft_odds_file = File(fp=draft_odds_bytes, filename="draft_odds.png")

            # Send file
            await ctx.respond(
                content="**Draft Odds for Next Season:**",
                files=[draft_odds_file]
            )
            logging.info(f"Sent draft odds to {ctx.author} in channel {ctx.channel.id}")

        except Exception as e:
            await ctx.respond("An error occurred while generating draft odds.", ephemeral=True)
            logging.error(f"Error in draft_odds command: {e}")

def create_radar_chart(player):
    """
    Generate a radar chart for the specified player.
    Returns image bytes.
    """
    import plotly.graph_objects as go
    import pandas as pd

    radar_metrics = [
        "Avg Score", "Goals Per Game", "Assists Per Game", 
        "Saves Per Game", "Shots Per Game", "Big Boost Stolen",
        "Small Boost Stolen", "Demos Differential"
    ]
    
    values = player[radar_metrics].values.flatten().tolist()
    values += values[:1]  # To close the radar chart
    
    fig = go.Figure(
        data=[
            go.Scatterpolar(r=values, theta=radar_metrics + [radar_metrics[0]], fill='toself', name=player['Player'])
        ]
    )
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor='#d7be79'
        ),
        showlegend=False,
        title=f"Relative Skill Chart: {player['Player']}",
    )
    
    buffer = io.BytesIO()
    fig.write_image(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()

def create_kpi_panel(player):
    """
    Generate a KPI panel image for the specified player.
    Returns image bytes.
    """
    from PIL import Image, ImageDraw, ImageFont

    # Create an image with white background
    img = Image.new('RGB', (400, 600), color='#d7be79')
    draw = ImageDraw.Draw(img)

    # Load a TrueType or OpenType font file, and create a font object
    try:
        font = ImageFont.truetype("arial.ttf", size=24)
        title_font = ImageFont.truetype("arial.ttf", size=30)
    except IOError:
        # If the font file is not found, use the default font
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    # Title
    title_text = "Key Performance Indicators"
    title_width, title_height = draw.textsize(title_text, font=title_font)
    title_x = (img.width - title_width) // 2
    title_y = 20
    draw.text((title_x, title_y), title_text, font=title_font, fill=(25, 25, 112))

    # Player Stats
    stats_to_display = [
        ("Dominance Quotient", player["Dominance Quotient"]),
        ("Avg Score", player["Avg Score"]),
        ("Goals Per Game", player["Goals Per Game"]),
        ("Assists Per Game", player["Assists Per Game"]),
        ("Saves Per Game", player["Saves Per Game"]),
        ("Shots Per Game", player["Shots Per Game"]),
        ("Demos Inf. Per Game", player["Demos Inf. Per Game"]),
        ("Demos Taken Per Game", player["Demos Taken Per Game"]),
        ("Big Boost Stolen", player["Big Boost Stolen"]),
        ("Small Boost Stolen", player["Small Boost Stolen"]),
    ]

    box_width = 360
    box_height = 40
    start_x = 20
    start_y = 80
    padding = 20
    font_color = (25, 25, 112)

    for idx, (label, value) in enumerate(stats_to_display):
        x = start_x
        y = start_y + idx * (box_height + padding)
        # Draw rectangle
        draw.rectangle([x, y, x + box_width, y + box_height], fill=(173, 216, 230))
        # Draw text
        stat = f"{label}: {value:.2f}"
        text_width, text_height = draw.textsize(stat, font=font)
        text_x = x + (box_width - text_width) // 2
        text_y = y + (box_height - text_height) // 2
        draw.text((text_x, text_y), stat, font=font, fill=font_color)

    # Save to BytesIO
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()

def create_draft_odds_table(final_df):
    """
    Generate a draft odds table image.
    Returns image bytes.
    """
    import matplotlib.pyplot as plt

    # Example logic: Sort teams by EPI Score and assign draft odds
    sorted_teams = final_df.sort_values('EPI Score', ascending=False).reset_index(drop=True)
    sorted_teams['Draft_Odds (%)'] = (sorted_teams.index + 1) * 2  # Simplified example

    # Select relevant columns
    draft_odds = sorted_teams[['Team', 'Draft_Odds (%)']]

    # Plot table using matplotlib
    fig, ax = plt.subplots(figsize=(6, len(draft_odds)*0.5 + 1))
    ax.axis('off')
    table = ax.table(cellText=draft_odds.values, colLabels=draft_odds.columns, loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 1.5)

    # Save to BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='PNG', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()

def create_radar_chart(player):
    """
    Placeholder function to create a radar chart for a player.
    Replace with actual implementation.
    """
    import plotly.graph_objects as go
    import pandas as pd

    radar_metrics = [
        "Avg Score", "Goals Per Game", "Assists Per Game", 
        "Saves Per Game", "Shots Per Game", "Big Boost Stolen",
        "Small Boost Stolen", "Demos Differential"
    ]
    
    values = player[radar_metrics].values.flatten().tolist()
    values += values[:1]  # To close the radar chart
    
    fig = go.Figure(
        data=[
            go.Scatterpolar(r=values, theta=radar_metrics + [radar_metrics[0]], fill='toself', name=player['Player'])
        ]
    )
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
            bgcolor='#d7be79'
        ),
        showlegend=False,
        title=f"Relative Skill Chart: {player['Player']}",
    )
    
    buffer = BytesIO()
    fig.write_image(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()

def create_kpi_panel(player):
    """
    Generate a KPI panel image for the specified player.
    Returns image bytes.
    """
    from PIL import Image, ImageDraw, ImageFont

    # Create an image with white background
    img = Image.new('RGB', (400, 600), color='#d7be79')
    draw = ImageDraw.Draw(img)

    # Load a TrueType or OpenType font file, and create a font object
    try:
        font = ImageFont.truetype("arial.ttf", size=24)
        title_font = ImageFont.truetype("arial.ttf", size=30)
    except IOError:
        # If the font file is not found, use the default font
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()

    # Title
    title_text = "Key Performance Indicators"
    title_width, title_height = draw.textsize(title_text, font=title_font)
    title_x = (img.width - title_width) // 2
    title_y = 20
    draw.text((title_x, title_y), title_text, font=title_font, fill=(25, 25, 112))

    # Player Stats
    stats_to_display = [
        ("Dominance Quotient", player["Dominance Quotient"]),
        ("Avg Score", player["Avg Score"]),
        ("Goals Per Game", player["Goals Per Game"]),
        ("Assists Per Game", player["Assists Per Game"]),
        ("Saves Per Game", player["Saves Per Game"]),
        ("Shots Per Game", player["Shots Per Game"]),
        ("Demos Inf. Per Game", player["Demos Inf. Per Game"]),
        ("Demos Taken Per Game", player["Demos Taken Per Game"]),
        ("Big Boost Stolen", player["Big Boost Stolen"]),
        ("Small Boost Stolen", player["Small Boost Stolen"]),
    ]

    box_width = 360
    box_height = 40
    start_x = 20
    start_y = 80
    padding = 20
    font_color = (25, 25, 112)

    for idx, (label, value) in enumerate(stats_to_display):
        x = start_x
        y = start_y + idx * (box_height + padding)
        # Draw rectangle
        draw.rectangle([x, y, x + box_width, y + box_height], fill=(173, 216, 230))
        # Draw text
        stat = f"{label}: {value:.2f}"
        text_width, text_height = draw.textsize(stat, font=font)
        text_x = x + (box_width - text_width) // 2
        text_y = y + (box_height - text_height) // 2
        draw.text((text_x, text_y), stat, font=font, fill=font_color)

    # Save to BytesIO
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()

def create_draft_odds_table(final_df):
    """
    Generate a draft odds table image.
    Returns image bytes.
    """
    import matplotlib.pyplot as plt

    # Example logic: Sort teams by EPI Score and assign draft odds
    sorted_teams = final_df.sort_values('EPI Score', ascending=False).reset_index(drop=True)
    sorted_teams['Draft_Odds (%)'] = (sorted_teams.index + 1) * 2  # Simplified example

    # Select relevant columns
    draft_odds = sorted_teams[['Team', 'Draft_Odds (%)']]

    # Plot table using matplotlib
    fig, ax = plt.subplots(figsize=(6, len(draft_odds)*0.5 + 1))
    ax.axis('off')
    table = ax.table(cellText=draft_odds.values, colLabels=draft_odds.columns, loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 1.5)

    # Save to BytesIO
    buffer = BytesIO()
    plt.savefig(buffer, format='PNG', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()
