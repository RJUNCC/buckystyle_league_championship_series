# src/app.py
import streamlit as st
from database.database import Database
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def main():
    st.title("Buckystyle League Teams")

    db = Database()
    teams_df = db.fetch_teams_dataframe()
    db.close()

    if teams_df.empty:
        st.write("No teams found.")
        return

    # Display the DataFrame
    st.subheader("Team Statistics")
    st.dataframe(teams_df)

    # Example Visualization: EPI Score Distribution
    st.subheader("EPI Score Distribution")
    fig, ax = plt.subplots()
    sns.histplot(teams_df['EPI Score'], bins=10, kde=True, ax=ax, color='blue')
    ax.set_xlabel("EPI Score")
    ax.set_ylabel("Frequency")
    st.pyplot(fig)

    # Games Played vs EPI Score
    st.subheader("Games Played vs EPI Score")
    fig, ax = plt.subplots()
    sns.scatterplot(data=teams_df, x='Games', y='EPI Score', hue='EPI Rank', palette='viridis', ax=ax)
    ax.set_xlabel("Games Played")
    ax.set_ylabel("EPI Score")
    ax.set_title("Games Played vs EPI Score")
    st.pyplot(fig)

    # Key Performance Indicators
    st.subheader("Key Performance Indicators")
    col1, col2, col3 = st.columns(3)
    col1.metric("Average EPI Score", f"{teams_df['EPI Score'].mean():.2f}")
    col2.metric("Total Games", f"{teams_df['Games'].sum()}")
    col3.metric("Average Goals For", f"{teams_df['Goals_For'].mean():.2f}")

    # Additional Visualizations
    st.subheader("Goals For vs Goals Against")
    fig, ax = plt.subplots()
    sns.scatterplot(data=teams_df, x='Goals_For', y='Goals_Against', hue='Strength of Schedule', palette='coolwarm', ax=ax)
    ax.set_xlabel("Goals For")
    ax.set_ylabel("Goals Against")
    ax.set_title("Goals For vs Goals Against")
    st.pyplot(fig)

if __name__ == "__main__":
    main()
