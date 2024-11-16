import pandas as pd

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
