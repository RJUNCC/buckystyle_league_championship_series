import pandas as pd
import matplotlib.pyplot as plt

# Apply styling
def highlight_rank(s):
        if s.name in ["Player", "Dominance Quotient"]:
            return ['color: #f8f8f2;'] * len(s)
        
        # Reverse color scheme for "Demos Taken Per Game"
        if s.name == "Demos Taken Per Game":
            return ['color: lightcoral; font-weight: bold;' if v == s.max() else
                    'color: limegreen; font-weight: bold;' if v == s.min() else
                    'color: #f8f8f2;' for v in s]
        
        # Standard color scheme for all other columns
        return ['color: limegreen; font-weight: bold;' if v == s.max() else
                'color: lightcoral; font-weight: bold;' if v == s.min() else
                'color: #f8f8f2;' for v in s]

def make_highlighted_table(df: pd.DataFrame) -> None:
    """
    Apply styling to the DataFrame and display it in a Jupyter notebook.
    Args:
        df (pd.DataFrame): DataFrame to be styled.
    """
    styled_df = df.style.apply(highlight_rank, subset=df.columns)\
        .format({
            'Dominance Quotient': '{:.2f}', 
            'Avg Score': '{:.2f}',         
            'Goals Per Game': '{:.2f}',           
            'Assists Per Game': '{:.2f}',      
            'Saves Per Game': '{:.2f}',           
            'Shots Per Game': '{:.2f}',       
            'Shooting %': '{:.2%}',  # Convert back to percentage format
            'Demos Inf. Per Game': '{:.2f}',
            'Demos Taken Per Game': '{:.2f}',
            'Big Boost Stolen': '{:.2f}',
            'Small Boost Stolen': '{:.2f}'
        })\
        .set_properties(**{'text-align': 'center'})\
        .set_table_styles([
            {'selector': 'thead th', 'props': 'color: #f8f8f2; background-color: #282a36;'},
            {'selector': 'tbody tr:nth-child(even) td, tbody tr:nth-child(even) th', 
                'props': 'background-color: #44475a;'},
            {'selector': 'tbody tr:nth-child(odd) td, tbody tr:nth-child(odd) th', 
                'props': 'background-color: #282a36;'},
            {'selector': 'td, th', 'props': 'border: none; text-align: center;'},
            {'selector': '.row_heading, .blank', 'props': 'color: #f8f8f2; background-color: #282a36;'}
        ], overwrite=False)
    
    return styled_df

def team_styled_table(df: pd.DataFrame) -> None:
    team_df = df.style.format({
        'EPI Score': '{:.2f}', 
        'Roster Rating': '{:.2f}',         
        'Goals For': '{:.2f}',           
        'Goals Against': '{:.2f}',      
        'Shots For': '{:.2f}',           
        'Shots Against': '{:.2f}',       
        'Strength of Schedule': '{:.2f}' 
    }).set_table_styles([
        {'selector': 'thead th', 'props': 'color: #f8f8f2; background-color: #282a36;'},
        {'selector': 'tbody tr:nth-child(even) td, tbody tr:nth-child(even) th', 
            'props': 'background-color: #44475a; color: #f8f8f2;'},
        {'selector': 'tbody tr:nth-child(odd) td, tbody tr:nth-child(odd) th', 
            'props': 'background-color: #282a36; color: #f8f8f2;'},
        {'selector': 'td, th', 'props': 'border: none;'}
    ], overwrite=False)
    
    return team_df

def export_styled_table(df, output_path):
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(20, 4))
    ax.axis('off')
    
    # Create table
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc='center',
        cellLoc='center'
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    
    # Apply custom colors
    for (row, col), cell in table.get_celld().items():
        if row == 0:  # Header
            cell.set_text_props(color='#f8f8f2')
            cell.set_facecolor('#44475a')
        elif row % 2 == 0:  # Even rows
            cell.set_facecolor('#44475a')
            cell.set_text_props(color='#f8f8f2')
        else:  # Odd rows
            cell.set_facecolor('#282a36')
            cell.set_text_props(color='#f8f8f2')
        
        # Remove cell borders
        cell.set_edgecolor('none')
    
    # Save with tight layout and high DPI
    plt.savefig(
        output_path,
        bbox_inches='tight',
        dpi=150,
        facecolor='#282a36'
    )
    plt.close()

def create_styled_table(df, output_path):
    fig, ax = plt.subplots(figsize=(15, len(df) * 0.5))
    ax.axis('off')
    
    # Create the table
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc='center',
        cellLoc='center'
    )
    
    # Style settings
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    
    # Apply styling to each cell
    for (row, col), cell in table.get_celld().items():
        # Remove borders
        cell.set_edgecolor('none')
        
        # Header styling
        if row == 0:
            cell.set_facecolor('#282a36')
            cell.set_text_props(color='#f8f8f2')
        else:
            # Alternating row colors
            cell.set_facecolor('#282a36' if row % 2 == 1 else '#44475a')
            
            # Get the value for comparison
            if col < len(df.columns):
                value = df.iloc[row-1, col]
                column_name = df.columns[col]
                
                # Default text color
                text_color = '#f8f8f2'
                
                # Special handling for specific columns
                if column_name not in ['Player', 'Dominance Quotient']:
                    col_max = df[column_name].max()
                    col_min = df[column_name].min()
                    
                    if column_name == 'Demos Taken Per Game':
                        if value == col_max:
                            text_color = 'lightcoral'
                        elif value == col_min:
                            text_color = 'limegreen'
                    else:
                        if value == col_max:
                            text_color = 'limegreen'
                        elif value == col_min:
                            text_color = 'lightcoral'
                
                cell.set_text_props(color=text_color, weight='bold' if text_color in ['limegreen', 'lightcoral'] else 'normal')
            
            cell.set_text_props(color=text_color)
    
    # Save with proper background
    plt.savefig(
        output_path,
        bbox_inches='tight',
        dpi=300,
        facecolor='#282a36',
        edgecolor='none'
    )
    plt.close()
