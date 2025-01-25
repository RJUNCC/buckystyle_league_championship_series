import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Set page title
st.title("Player Statistics Dashboard")

# Function to create radar chart
def create_radar_chart(player_data):
    categories = [
        'Avg Score', 'Goals Per Game', 'Assists Per Game',
        'Saves Per Game', 'Shots Per Game', 'K/D'
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
                showticklabels=False,
                showline=False,
                ticks="",
                range=[0, 1]
            )
        ),
        showlegend=True
    )
    
    return fig

def calculate_kpis(player_df, player):
    # Calculate rankings for each stat
    player_df['Demo KD'] = player_df['Demos Inf. Per Game'] / player_df['Demos Taken Per Game']
    
    metrics = {
        'Avg Score': 'Avg Score',
        'Goals': 'Goals Per Game',
        'Assists': 'Assists Per Game',
        'Saves': 'Saves Per Game',
        'Shots': 'Shots Per Game',
        'K/D Ratio': 'Demo KD'
    }
    
    # Calculate rankings
    rankings = {}
    for name, col in metrics.items():
        player_df[f'{col}_rank'] = player_df[col].rank(ascending=False)
        rankings[name] = int(player_df[player_df['Player'] == player][f'{col}_rank'].iloc[0])
    
    return rankings

def display_ranking(rank, total=30):
    normalized = (rank - 1) / (total - 1)
    color = f'rgb({int(255 * normalized)}, {int(255 * (1-normalized))}, 0)'
    return f'<span style="color: {color}">#{rank}</span>'

# Load the parquet data
@st.cache_data
def load_data():
    try:
        return pd.read_parquet('data/parquet/season_3_all_data.parquet')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

@st.cache_data
def load_player_data():
    try:
        return pd.read_parquet('data/parquet/season_3_player_data.parquet')
    except Exception as e:
        st.error(f"Error loading player data: {str(e)}")
        return None

# Load both datasets
df = load_data()
player_df = load_player_data()

# Create the scaler object
scaler = MinMaxScaler()

if df is not None and player_df is not None:
    selected_player = st.selectbox(
        'Select Player:',
        options=df['Player'].unique()
    )

    # Calculate K/D ratio first
    df['K/D'] = df['Demos Inf. Per Game'] / df['Demos Taken Per Game']
    
    # Columns to normalize
    stats_columns = ['Avg Score', 'Goals Per Game', 
                    'Assists Per Game', 'Saves Per Game', 
                    'Shots Per Game', 'K/D']
    
    # Fit and transform all stats at once
    df[stats_columns] = scaler.fit_transform(df[stats_columns])
    
    if selected_player:
        # Display Rankings
        st.markdown("## Player Rankings")
        rankings = calculate_kpis(player_df, selected_player)
        for stat, rank in rankings.items():
            st.markdown(f"**{stat}**: {display_ranking(rank)}", unsafe_allow_html=True)
        
        # Display Radar Chart
        st.markdown("## Radar Chart")
        player_stats = df[df['Player'] == selected_player].iloc[0]
        stats_values = [
            player_stats['Avg Score'],
            player_stats['Goals Per Game'],
            player_stats['Assists Per Game'],
            player_stats['Saves Per Game'],
            player_stats['Shots Per Game'],
            player_stats['K/D']
        ]
        
        radar_chart = create_radar_chart(stats_values)
        st.plotly_chart(radar_chart)
