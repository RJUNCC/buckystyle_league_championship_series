import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Set page title
st.title("Player Statistics Radar Chart")

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

# Create the scaler object
scaler = MinMaxScaler()

if df is not None:
    selected_player = st.selectbox(
        'Search for a player:',
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
