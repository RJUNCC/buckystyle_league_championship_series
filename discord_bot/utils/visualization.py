# # discord_bot/utils/visualization.py
# import plotly.graph_objects as go
# import matplotlib.pyplot as plt
# import io
# import dataframe_image as dfi

# def create_radar_chart(player):
#     metrics = [
#         "Avg_Score", 
#         "Goals_Per_Game", 
#         "Assists_Per_Game", 
#         "Saves_Per_Game", 
#         "Shots_Per_Game", 
#         "Demos_Inf_Per_Game", 
#         "Demos_Taken_Per_Game", 
#         "Big_Boost_Stolen", 
#         "Small_Boost_Stolen"
#     ]

#     values = player[metrics].values.flatten().tolist()
#     values += values[:1]  # Close the loop

#     labels = metrics + metrics[:1]

#     fig = go.Figure(
#         data=[
#             go.Scatterpolar(r=values, theta=labels, fill='toself', name=player['Player'], mode='lines+markers')
#         ]
#     )

#     fig.update_layout(
#         polar=dict(
#             radialaxis=dict(visible=True, range=[0, max(values) + 10]),
#             bgcolor='#d7be79'
#         ),
#         showlegend=False,
#         title=f"Relative Skill Chart: {player['Player']}",
#     )

#     img_bytes = fig.to_image(format="png")
#     return img_bytes

# def create_kpi_panel(player):
#     fig, ax = plt.subplots(figsize=(4, 6))
#     ax.axis('off')
#     kpis = {
#         "Dominance Quotient": player['Dominance_Quotient'],
#         "Avg Score": player['Avg_Score'],
#         "Goals Per Game": player['Goals_Per_Game'],
#         "Assists Per Game": player['Assists_Per_Game'],
#         "Saves Per Game": player['Saves_Per_Game'],
#         "Shots Per Game": player['Shots_Per_Game'],
#         "Demos Inf. Per Game": player['Demos_Inf_Per_Game'],
#         "Demos Taken Per Game": player['Demos_Taken_Per_Game'],
#         "Big Boost Stolen": player['Big_Boost_Stolen'],
#         "Small Boost Stolen": player['Small_Boost_Stolen']
#     }

#     y_pos = 0.9
#     for label, value in kpis.items():
#         ax.text(0.1, y_pos, f"{label}: {value}", fontsize=12, ha='left', va='center')
#         y_pos -= 0.05

#     buf = io.BytesIO()
#     plt.savefig(buf, format='png', bbox_inches='tight')
#     buf.seek(0)
#     plt.close(fig)
#     return buf

# def create_team_table_image(df):
#     styled_df = df.style.format({
#         'EPI_Score': '{:.2f}', 
#         'Roster_Rating': '{:.2f}',         
#         'Goals_For': '{:.2f}',           
#         'Goals_Against': '{:.2f}',      
#         'Shots_For': '{:.2f}',           
#         'Shots_Against': '{:.2f}',       
#         'Strength_of_Schedule': '{:.2f}' 
#     }).set_table_styles([
#         {'selector': 'thead th', 'props': 'color: #f8f8f2; background-color: #282a36;'},
#         {'selector': 'tbody tr:nth-child(even) td, tbody tr:nth-child(even) th', 'props': 'background-color: #44475a; color: #f8f8f2;'},
#         {'selector': 'tbody tr:nth-child(odd) td, tbody tr:nth-child(odd) th', 'props': 'background-color: #282a36; color: #f8f8f2;'},
#         {'selector': 'td, th', 'props': 'border: none; text-align: center;'},
#         {'selector': '.row_heading, .blank', 'props': 'color: #f8f8f2; background-color: #282a36;'}
#     ], overwrite=False)
    
#     buf = io.BytesIO()
#     dfi.export(styled_df, buf, format='png')
#     buf.seek(0)
#     return buf.read()

# discord_bot/utils/visualization.py
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import io

def create_radar_chart(player):
    # Example radar chart creation
    labels = ['Points', 'Assists', 'Rebounds', 'Steals', 'Blocks']
    stats = [
        player.get('points', 0),
        player.get('assists', 0),
        player.get('rebounds', 0),
        player.get('steals', 0),
        player.get('blocks', 0)
    ]

    # Number of variables
    num_vars = len(labels)

    # Compute angle of each axis
    angles = [n / float(num_vars) * 2 * 3.14159 for n in range(num_vars)]
    angles += angles[:1]  # Complete the loop

    stats += stats[:1]  # Complete the loop

    # Initialize plot
    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))

    # Draw the outline
    ax.plot(angles, stats, color='blue', linewidth=2)
    ax.fill(angles, stats, color='blue', alpha=0.25)

    # Fix axis to go in the right order and start at the top
    ax.set_theta_offset(3.14159 / 2)
    ax.set_theta_direction(-1)

    # Draw axis per variable
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    # Draw ylabels
    ax.set_rlabel_position(0)
    ax.set_yticks([10, 20, 30, 40, 50])
    ax.set_yticklabels(['10','20','30','40','50'], fontsize=7)
    ax.set_ylim(0,50)

    # Title
    ax.set_title(f"Radar Chart for {player['name']}", y=1.08)

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()

def create_kpi_panel(player):
    # Example KPI panel creation
    fig, ax = plt.subplots(figsize=(6,2))
    kpis = {
        'Points': player.get('points', 0),
        'Assists': player.get('assists', 0),
        'Rebounds': player.get('rebounds', 0)
    }
    sns.barplot(x=list(kpis.keys()), y=list(kpis.values()), palette='viridis', ax=ax)
    ax.set_ylim(0, max(kpis.values()) + 10)
    ax.set_title(f"KPI Panel for {player['name']}")
    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()

def create_team_table_image(teams_df):
    # Example team stats table as image
    fig, ax = plt.subplots(figsize=(10, len(teams_df) * 0.5))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=teams_df.values, colLabels=teams_df.columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.5)

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.read()
