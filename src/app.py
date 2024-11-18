# src/app.py

from flask import Flask, render_template, request, jsonify
import joblib
import pandas as pd
import os
import logging

app = Flask(__name__)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# Define the path to the pipeline
pipeline_path = os.path.join('..', 'data', 'processed', 'fantasy_pipeline.pkl')

# Load the trained pipeline
try:
    pipeline = joblib.load(pipeline_path)
    logging.info("Fantasy pipeline loaded successfully in Flask app.")
except Exception as e:
    logging.error(f"Error loading fantasy pipeline: {e}")
    pipeline = None

# Load current season data
current_season_path = os.path.join('..', 'data', 'parquet', 'current_season_data.parquet')
try:
    current_season_df = pd.read_parquet(current_season_path)
    current_season_df.fillna(current_season_df.median(), inplace=True)
    logging.info("Current season data loaded successfully in Flask app.")
except Exception as e:
    logging.error(f"Error loading current season data: {e}")
    current_season_df = pd.DataFrame()

@app.route('/')
def home():
    return render_template('index.html')  # Ensure 'index.html' exists in 'templates/'

@app.route('/predict', methods=['POST'])
def predict():
    if not pipeline:
        return jsonify({'error': 'Model is not loaded.'}), 500
    
    try:
        data = request.get_json()
        player_name = data.get('player_name', '').strip()
        
        if not player_name:
            return jsonify({'error': 'Player name is required.'}), 400
        
        # Search for the player (case-insensitive)
        player_data = current_season_df[current_season_df['Player'].str.lower() == player_name.lower()]
        if player_data.empty:
            return jsonify({'error': f"Player '{player_name}' not found."}), 404
        
        player = player_data.iloc[0]
        
        # Define feature columns
        feature_cols = [
            "Avg Score_prev",
            "Goals Per Game_prev",
            "Assists Per Game_prev",
            "Saves Per Game_prev",
            "Shots Per Game_prev",
            "Demos Inf. Per Game_prev",
            "Demos Taken Per Game_prev"
        ]
        
        # Check for missing features
        missing_features = [col for col in feature_cols if pd.isnull(player[col])]
        if missing_features:
            return jsonify({'error': f"Missing data for player '{player_name}': {', '.join(missing_features)}"}), 400
        
        # Prepare input for prediction
        X_new = player[feature_cols].values.reshape(1, -1)
        
        # Make prediction
        predicted_points = pipeline.predict(X_new)[0]
        
        # Return the result
        return jsonify({
            'player_name': player['Player'],
            'predicted_fantasy_points': round(predicted_points, 2)
        })
    
    except Exception as e:
        logging.error(f"Error during prediction: {e}")
        return jsonify({'error': 'An error occurred during prediction.'}), 500

if __name__ == '__main__':
    app.run(debug=True)
