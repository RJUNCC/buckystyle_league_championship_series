-- database/schema.sql

CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    team_name VARCHAR(255) UNIQUE NOT NULL,
    EPI_Score FLOAT,
    Roster_Rating FLOAT,
    Win_Percent VARCHAR(10),
    Goals_For FLOAT,
    Goals_Against FLOAT,
    Goal_Diff VARCHAR(10),
    Shots_For FLOAT,
    Shots_Against FLOAT,
    Shot_Diff VARCHAR(10),
    Strength_of_Schedule FLOAT,
    date DATE
);

CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    team_name VARCHAR(255) REFERENCES teams(team_name),
    player_name VARCHAR(255),
    Avg_Score FLOAT,
    Goals_Per_Game FLOAT,
    Assists_Per_Game FLOAT,
    Saves_Per_Game FLOAT,
    Shots_Per_Game FLOAT,
    Shooting_Percent VARCHAR(10),
    Demos_Inf_Per_Game FLOAT,
    Demos_Taken_Per_Game FLOAT,
    Big_Boost_Stolen FLOAT,
    Small_Boost_Stolen FLOAT,
    Avg_Score_Zscore FLOAT,
    Goals_Per_Game_Zscore FLOAT,
    Assists_Per_Game_Zscore FLOAT,
    Saves_Per_Game_Zscore FLOAT,
    Shots_Per_Game_Zscore FLOAT,
    Demos_Inf_Per_Game_Zscore FLOAT,
    Demos_Taken_Per_Game_Zscore FLOAT,
    Big_Boost_Stolen_Zscore FLOAT,
    Small_Boost_Stolen_Zscore FLOAT,
    Dominance_Quotient FLOAT
);
