# discord_bot/utils/visualization.py
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import dataframe_image as dfi

def create_radar_chart(player):
    metrics = [
        "Avg_Score", 
        "Goals_Per_Game", 
        "Assists_Per_Game", 
        "Saves_Per_Game", 
        "Shots_Per_Game", 
        "Demos_Inf_Per_Game", 
        "Demos_Taken_Per_Game", 
        "Big_Boost_Stolen", 
        "Small_Boost_Stolen"
    ]

    values = player[metrics].values.flatten().tolist()
    values += values[:1]  # Close the loop

    labels = metrics + metrics[:1]

    fig = go.Figure(
        data=[
            go.Scatterpolar(r=values, theta=labels, fill='toself', name=player['Player'], mode='lines+markers')
        ]
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(values) + 10]),
            bgcolor='#d7be79'
        ),
        showlegend=False,
        title=f"Relative Skill Chart: {player['Player']}",
    )

    img_bytes = fig.to_image(format="png")
    return img_bytes

def create_kpi_panel(player):
    fig, ax = plt.subplots(figsize=(4, 6))
    ax.axis('off')
    kpis = {
        "Dominance Quotient": player['Dominance_Quotient'],
        "Avg Score": player['Avg_Score'],
        "Goals Per Game": player['Goals_Per_Game'],
        "Assists Per Game": player['Assists_Per_Game'],
        "Saves Per Game": player['Saves_Per_Game'],
        "Shots Per Game": player['Shots_Per_Game'],
        "Demos Inf. Per Game": player['Demos_Inf_Per_Game'],
        "Demos Taken Per Game": player['Demos_Taken_Per_Game'],
        "Big Boost Stolen": player['Big_Boost_Stolen'],
        "Small Boost Stolen": player['Small_Boost_Stolen']
    }

    y_pos = 0.9
    for label, value in kpis.items():
        ax.text(0.1, y_pos, f"{label}: {value}", fontsize=12, ha='left', va='center')
        y_pos -= 0.05

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def create_team_table_image(df):
    styled_df = df.style.format({
        'EPI_Score': '{:.2f}', 
        'Roster_Rating': '{:.2f}',         
        'Goals_For': '{:.2f}',           
        'Goals_Against': '{:.2f}',      
        'Shots_For': '{:.2f}',           
        'Shots_Against': '{:.2f}',       
        'Strength_of_Schedule': '{:.2f}' 
    }).set_table_styles([
        {'selector': 'thead th', 'props': 'color: #f8f8f2; background-color: #282a36;'},
        {'selector': 'tbody tr:nth-child(even) td, tbody tr:nth-child(even) th', 'props': 'background-color: #44475a; color: #f8f8f2;'},
        {'selector': 'tbody tr:nth-child(odd) td, tbody tr:nth-child(odd) th', 'props': 'background-color: #282a36; color: #f8f8f2;'},
        {'selector': 'td, th', 'props': 'border: none; text-align: center;'},
        {'selector': '.row_heading, .blank', 'props': 'color: #f8f8f2; background-color: #282a36;'}
    ], overwrite=False)
    
    buf = io.BytesIO()
    dfi.export(styled_df, buf, format='png')
    buf.seek(0)
    return buf.read()