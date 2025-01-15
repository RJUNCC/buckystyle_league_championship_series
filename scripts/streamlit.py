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
def create_radar_chart(player_data):
    categories = [
        'Avg Score', 'Goals Per Game', 'Assists Per Game',
        'Saves Per Game', 'Shots Per Game', 'Demo Differential'
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=player_data,
        theta=categories,
        fill='toself',
        name=selected_player
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=False,  # Hide the number labels
                showline=False,        # Hide the radial lines
                ticks="",             # Remove tick marks
                range=[0, max(player_data) * 1.2]
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

if df is not None:
    # Create search bar
    selected_player = st.selectbox(
        'Search for a player:',
        options=df['Player'].unique()
    )

    # Display radar chart when player is selected
    if selected_player:
        player_stats = df[df['Player'] == selected_player].iloc[0]
        stats_values = [
            player_stats['Avg Score Zscore'],
            player_stats['Goals Per Game Zscore'],
            player_stats['Assists Per Game Zscore'],
            player_stats['Saves Per Game Zscore'],
            player_stats['Shots Per Game Zscore'],
            minmax_scale(np.array(player_stats['Demos Inf. Per Game']) - np.array(player_stats['Demos Taken Per Game'])),
        ]
        
        radar_chart = create_radar_chart(stats_values)
        st.plotly_chart(radar_chart)
