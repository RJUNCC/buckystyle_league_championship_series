use csv::ReaderBuilder;
use nalgebra::DMatrix;
use std::collections::HashMap;
use std::error::Error;
use std::fs::File;
use std::io::BufReader;

#[derive(serde::Deserialize, Debug)]
struct Player {
    #[serde(rename(deserialize = "Player"))]
    player: String,
    #[serde(rename(deserialize = "Dominance Quotient"))]
    dominance_quotient: f64,
    #[serde(rename(deserialize = "Avg Score"))]
    avg_score: f64,
    #[serde(rename(deserialize = "Goals Per Game"))]
    goals_per_game: f64,
    #[serde(rename(deserialize = "Assists Per Game"))]
    assists_per_game: f64,
    #[serde(rename(deserialize = "Saves Per Game"))]
    saves_per_game: f64,
    #[serde(rename(deserialize = "Shots Per Game"))]
    shots_per_game: f64,
    #[serde(rename(deserialize = "Shooting %"))]
    shooting_percentage: f64,
    #[serde(rename(deserialize = "Demos Inf. Per Game"))]
    demos_inf_per_game: f64,
    #[serde(rename(deserialize = "Demos Taken Per Game"))]
    demos_taken_per_game: f64,
}

fn main() -> Result<(), csv::Error> {
    let file_name: &str = "../data/processed/previous_season_player_data.csv";
    let mut builder = ReaderBuilder::new();
    builder.double_quote(false).has_headers(true);
    let result = builder.from_path(file_name);

    if result.is_err() {
        println!("Failed to read CSV. File path probably doesn't exist, or is incorrect.");
        std::process::exit(9);
    }

    let mut rdr = result.unwrap();

    for record in rdr.deserialize() {
        let player: Player = record.unwrap();
        println!("Player Name: {}", player.player);
        println!("Dominance Quotient: {}", player.dominance_quotient);
        println!("Average Score: {}", player.avg_score);
        println!("Goals Per Game: {}", player.goals_per_game);
        println!("Assists Per Game: {}", player.assists_per_game);
        println!("Saves Per Game: {}", player.saves_per_game);
        println!("Shots Per Game: {}", player.shots_per_game);
        println!("Shooting Percentage: {}", player.shooting_percentage);
        println!("Demos Inflicted Per Game: {}", player.demos_inf_per_game);
        println!("Demos Taken Per Game: {}", player.demos_taken_per_game);
        println!(
            "Total Fantasy Point: {}",
            (5.0 * player.goals_per_game
                + 2.0 * player.assists_per_game
                + 3.5 * player.saves_per_game
                + 1.0 * player.shots_per_game
                + 0.5 * player.demos_inf_per_game
                - 0.5 * player.demos_taken_per_game)
                * 100.0
        );
    }

    Ok(())
}
