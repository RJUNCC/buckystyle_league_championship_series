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
    # First display games played in a centered box above the KPIs
    games_played = player_values['Games Played']
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; display: inline-block;">
                <h3 style="margin: 0; font-weight: bold;">Games Played: {int(games_played)}</h3>
            </div>
        </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)

    for i, (stat, col) in enumerate(metrics.items()):
        value = player_values[col]
        rank = rankings[stat]

        if rank <= 15:
            # Dark blue (0, 0, 139) to light blue (173, 216, 230)
            intensity = (rank - 1) / 14  # 0 for rank 1 (darkest), 1 for rank 15 (lightest)
            red = int(173 * intensity)
            green = int(216 * intensity)
            blue = int(139 + (230 - 139) * intensity)
        else:
            # Light red (255, 200, 200) to dark red (139, 0, 0)
            intensity = (rank - 16) / 14  # 0 for rank 16 (lightest), 1 for rank 30 (darkest)
            red = int(255 - (255 - 139) * intensity)
            green = blue = int(200 * (1 - intensity))

        color = f'rgb({red}, {green}, {blue})'

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
        df1 = pd.read_parquet('data/parquet/season_3_all_data.parquet')
        df2 = pd.read_parquet('data/parquet/season_3_player_data.parquet')
        
        # Capitalize player names
        df1['Player'] = df1['Player'].str.title()
        df2['Player'] = df2['Player'].str.title()
        
        # Merge the dataframes
        df = df1.merge(df2[['Player', 'Dominance Quotient']], on='Player', how='left')
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load data
df = load_data()
scaler = MinMaxScaler()

if df is not None:
    selected_player = st.selectbox(
        'Select Player:',
        options=sorted(df['Player'].unique())
    )

    # Calculate K/D ratio
    df['K/D'] = df['Demos Inf. Per Game'] / df['Demos Taken Per Game']
    
    if selected_player:
        # Get player's Dominance Quotient
        player_dq = df[df['Player'] == selected_player]['Dominance Quotient'].iloc[0]
        
        # Display player name and Dominance Quotient at the top
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="margin: 0; font-weight: bold;">{selected_player}</h2>
                <p style="margin: 0; font-size: 24px; font-weight: bold; background-color: rgba(255, 255, 0, 0.3); display: inline-block; padding: 5px 10px; border-radius: 5px;">Dominance Quotient: {player_dq:.2f}</p>
            </div>
        """, unsafe_allow_html=True)
        
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
        
        # Get player values (non-normalized)
        player_values = df[df['Player'] == selected_player].iloc[0]
        
        # Normalize data for radar chart only
        radar_columns = ['Avg Score', 'Goals Per Game', 
                        'Assists Per Game', 'Saves Per Game', 
                        'Shots Per Game', 'K/D']
        df_radar = df[radar_columns].copy()
        df_radar = pd.DataFrame(scaler.fit_transform(df_radar), columns=radar_columns, index=df.index)
        
        # Display Radar Chart
        player_stats = df_radar.loc[df['Player'] == selected_player].iloc[0]
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
        
        # Display KPIs
        display_kpi_boxes(player_values, rankings, metrics, df)
