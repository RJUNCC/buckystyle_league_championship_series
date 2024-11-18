# discord_bot/cogs/predictions.py

from discord.ext import commands
import pandas as pd
import joblib
import os
import logging

class Predictions(commands.Cog):
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        # Define the path to the pipeline
        self.pipeline_path = os.path.join('..', 'data', 'processed', 'fantasy_pipeline.pkl')
        # Load the trained pipeline
        try:
            self.pipeline = joblib.load(self.pipeline_path)
            logging.info("Fantasy pipeline loaded successfully in Discord cog.")
        except Exception as e:
            logging.error(f"Error loading fantasy pipeline: {e}")
            self.pipeline = None
        # Load current season data
        current_season_path = os.path.join('..', 'data', 'parquet', 'current_season_data.parquet')
        try:
            self.current_season_df = pd.read_parquet(current_season_path)
            self.current_season_df.fillna(self.current_season_df.median(), inplace=True)
            logging.info("Current season data loaded successfully in Discord cog.")
        except Exception as e:
            logging.error(f"Error loading current season data: {e}")
            self.current_season_df = pd.DataFrame()

    @commands.command(name='predict_fantasy')
    async def predict_fantasy(self, ctx, *, player_name: str):
        """Predict fantasy points for a specified player."""
        if not self.pipeline:
            await ctx.send("Model is not loaded. Please try again later.")
            logging.error("Pipeline not loaded. Cannot make predictions.")
            return
        
        try:
            # Search for the player (case-insensitive)
            player_data = self.current_season_df[self.current_season_df['Player'].str.lower() == player_name.lower()]
            if player_data.empty:
                await ctx.send(f"Player '{player_name}' not found.")
                logging.warning(f"Player '{player_name}' not found by {ctx.author} in channel {ctx.channel.id}")
                return
            
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
                await ctx.send(f"Missing data for player '{player_name}': {', '.join(missing_features)}")
                logging.error(f"Missing features {missing_features} for player '{player_name}'")
                return
            
            # Prepare input for prediction
            X_new = player[feature_cols].values.reshape(1, -1)
            
            # Make prediction
            predicted_points = self.pipeline.predict(X_new)[0]
            
            # Format the response
            response = f"**Predicted Fantasy Points for {player['Player']}: {predicted_points:.2f}**"
            
            await ctx.send(response)
            logging.info(f"Sent fantasy prediction for '{player['Player']}' to {ctx.author} in channel {ctx.channel.id}")
        
        except Exception as e:
            await ctx.send("An error occurred while making the prediction.")
            logging.error(f"Error in predict_fantasy command: {e}")

def setup(bot):
    config = bot.config  # Assuming your bot has a 'config' attribute
    bot.add_cog(Predictions(bot, config))
