import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Set page title
st.title("Player Statistics Dashboard")

# Add CSS to remove anchor links
st.markdown("""
    <style>
        .stMarkdown a {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

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
        showlegend=False
    )
    
    return fig

def display_kpi_boxes(player_values, rankings, metrics, df):
    cols = st.columns(2)

    for i, (stat, col) in enumerate(metrics.items()):
        value = player_values[col]
        rank = rankings[stat]
        
        normalized = (value - df[col].min()) / (df[col].max() - df[col].min())
        color = f'rgb({int(255 * (1-normalized))}, {int(255 * normalized)}, 0)'
        
        with cols[i % 2]:
            st.markdown(
                f"""
                <div style="background-color: {color}; padding: 10px; border-radius: 5px; margin-bottom: 10px; text-align: center;">
                    <h3 style="margin: 0; font-weight: bold; text-align: center;" id="no-anchor">{stat}</h3>
                    <p style="margin: 0; font-size: 24px; font-weight: bold; text-align: center;">{value:.2f}</p>
                    <p style="margin: 0; font-size: 20px; font-weight: bold; text-align: center;">#{rank}</p>
                </div>
                """, 
                unsafe_allow_html=True
            )

@st.cache_data
def load_data():
    try:
        return pd.read_parquet('data/parquet/season_3_all_data.parquet')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load data
df = load_data()
scaler = MinMaxScaler()

if df is not None:
    selected_player = st.selectbox(
        'Select Player:',
        options=df['Player'].unique()
    )

    # Calculate K/D ratio
    df['K/D'] = df['Demos Inf. Per Game'] / df['Demos Taken Per Game']
    
    # Columns to normalize
    stats_columns = ['Avg Score', 'Goals Per Game', 
                    'Assists Per Game', 'Saves Per Game', 
                    'Shots Per Game', 'K/D']
    
    # Fit and transform all stats at once
    df[stats_columns] = scaler.fit_transform(df[stats_columns])
    
    if selected_player:
        metrics = {
            'Avg Score': 'Avg Score',
            'Goals': 'Goals Per Game',
            'Assists': 'Assists Per Game',
            'Saves': 'Saves Per Game',
            'Shots': 'Shots Per Game',
            'K/D Ratio': 'K/D'
        }
        
        # Calculate rankings
        rankings = {}
        for name, col in metrics.items():
            df[f'{col}_rank'] = df[col].rank(ascending=False)
            rankings[name] = int(df[df['Player'] == selected_player][f'{col}_rank'].iloc[0])
        
        # Get player values
        player_values = df[df['Player'] == selected_player].iloc[0]
        
        # Display Radar Chart first
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
        
        # Display KPIs below the radar chart
        display_kpi_boxes(player_values, rankings, metrics, df)
