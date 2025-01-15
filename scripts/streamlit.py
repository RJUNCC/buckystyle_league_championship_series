import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Set page title
st.title("Player Statistics Radar Chart")

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
            player_stats['Avg Score'],
            player_stats['Goals Per Game'],
            player_stats['Assists Per Game'],
            player_stats['Saves Per Game'],
            player_stats['Shots Per Game'],
            player_stats['Demos Inf. Per Game'] - player_stats['Demos Taken Per Game'],
        ]
        
        radar_chart = create_radar_chart(stats_values)
        st.plotly_chart(radar_chart)
