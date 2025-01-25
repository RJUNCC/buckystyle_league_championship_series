import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# Set page title
st.title("Player Statistics Radar Chart")

def minmax_scale(data):
    min_val = np.min(data)
    max_val = np.max(data)
    return (data - min_val) / (max_val - min_val)

# Function to create radar chart
def create_radar_chart(player_data, global_min, global_max):
    categories = [
        'Avg Score', 'Goals Per Game', 'Assists Per Game',
        'Saves Per Game', 'Shots Per Game', 'K/D'
    ]
    
    # Scale the data using global min and max
    scaled_data = (player_data - global_min) / (global_max - global_min)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=scaled_data,
        theta=categories,
        fill='toself',
        name=selected_player
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,
                showline=False,
                ticks="",
                range=[0, 2]  # Fixed range from 0 to 1
            )
        ),
        showlegend=True
    )
    
    return fig

# Load the parquet data
@st.cache_data
def load_data():
    try:
        return pd.read_parquet('data/parquet/season_3_all_data.parquet')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load the data
df = load_data()

# In your main code, calculate global min and max
if df is not None:
    selected_player = st.selectbox(
        'Search for a player:',
        options=df['Player'].unique()
    )

    # Calculate global min and max for all stats
    stats_columns = ['Avg Score Zscore', 'Goals Per Game Zscore', 
                    'Assists Per Game Zscore', 'Saves Per Game Zscore', 
                    'Shots Per Game Zscore']

    global_min = df[stats_columns].min().min()
    global_max = df[stats_columns].max().max()

    # Calculate K/D ratio for all players
    df['K/D'] = (abs(df['Demos Inf. Per Game']) / abs(df['Demos Taken Per Game'])) / 5
    kd_min = df['K/D'].min()
    kd_max = df['K/D'].max()

    if selected_player:
        player_stats = df[df['Player'] == selected_player].iloc[0]
        stats_values = [
            player_stats['Avg Score Zscore'],
            player_stats['Goals Per Game Zscore'],
            player_stats['Assists Per Game Zscore'],
            player_stats['Saves Per Game Zscore'],
            player_stats['Shots Per Game Zscore'],
            ((player_stats['Demos Inf. Per Game'] / 
            player_stats['Demos Taken Per Game'] - kd_min) / (kd_max - kd_min)) / 5
        ]

        st.table(data=player_stats)
        
        radar_chart = create_radar_chart(stats_values, global_min, global_max)
        st.plotly_chart(radar_chart)


