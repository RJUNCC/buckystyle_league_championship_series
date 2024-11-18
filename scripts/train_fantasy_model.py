import pandas as pd
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, r2_score

import matplotlib.pyplot as plt
import seaborn as sns

import warnings
warnings.filterwarnings("ignore")

import optuna
import logging
import xgboost
import lightgbm
import numpy as np
import os
import sys
import joblib
from pathlib import Path

def load_data():
    # Define paths
    data_path_prev = Path('../data/parquet/previous_season_player_data.parquet')
    data_path_current = Path('../data/parquet/current_season_data.parquet')  # Adjust if different
    
    # Load data
    prev_season_df = pd.read_parquet(data_path_prev)
    current_season_df = pd.read_parquet(data_path_current)
    
    # Handle missing values
    prev_season_df.fillna(prev_season_df.median(), inplace=True)
    current_season_df.fillna(current_season_df.median(), inplace=True)
    
    # Rename and merge datasets
    prev_season_df = prev_season_df.add_suffix('_prev')
    prev_season_df = prev_season_df.rename(columns={'Player_prev': 'Player'})
    merged_df = pd.merge(prev_season_df, current_season_df, on='Player', how='inner')
    
    return merged_df

def objective(trial, X_train, y_train, X_valid, y_valid, feature_cols):
    # Suggest model type
    model_name = trial.suggest_categorical('model', ['RandomForest', 'XGBoost', 'LightGBM'])
    
    # Common pipeline steps
    scaler = StandardScaler()
    poly = PolynomialFeatures(degree=2, include_bias=False)
    
    # Define and suggest hyperparameters based on the model
    if model_name == 'RandomForest':
        n_estimators = trial.suggest_int('rf_n_estimators', 100, 1000)
        max_depth = trial.suggest_int('rf_max_depth', 10, 50)
        min_samples_split = trial.suggest_int('rf_min_samples_split', 2, 10)
        
        regressor = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=42
        )
        
    elif model_name == 'XGBoost':
        n_estimators = trial.suggest_int('xgb_n_estimators', 100, 1000)
        max_depth = trial.suggest_int('xgb_max_depth', 3, 10)
        learning_rate = trial.suggest_loguniform('xgb_learning_rate', 1e-4, 1e-1)
        subsample = trial.suggest_uniform('xgb_subsample', 0.5, 1.0)
        
        regressor = xgboost.XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            objective='reg:squarederror',
            eval_metric='rmse',
            random_state=42,
            verbosity=0
        )
        
    elif model_name == 'LightGBM':
        n_estimators = trial.suggest_int('lgbm_n_estimators', 100, 1000)
        max_depth = trial.suggest_int('lgbm_max_depth', -1, 50)
        learning_rate = trial.suggest_loguniform('lgbm_learning_rate', 1e-4, 1e-1)
        num_leaves = trial.suggest_int('lgbm_num_leaves', 20, 300)
        subsample = trial.suggest_uniform('lgbm_subsample', 0.5, 1.0)
        
        regressor = lightgbm.LGBMRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
            subsample=subsample,
            random_state=42
        )
    
    # Create the pipeline
    pipeline = Pipeline([
        ('scaler', scaler),
        ('poly_features', poly),
        ('regressor', regressor)
    ])
    
    # Train the pipeline
    pipeline.fit(X_train, y_train)
    
    # Predict on validation set
    preds = pipeline.predict(X_valid)
    
    # Calculate MSE
    mse = mean_squared_error(y_valid, preds)
    
    return mse

def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Load data
    merged_df = load_data()
    logger.info("Data loaded and merged successfully.")
    
    # Define features and target
    feature_cols = [
        "Avg Score_prev",
        "Goals Per Game_prev",
        "Assists Per Game_prev",
        "Saves Per Game_prev",
        "Shots Per Game_prev",
        "Demos Inf. Per Game_prev",
        "Demos Taken Per Game_prev"
    ]
    target_col = "Avg Score"
    
    X = merged_df[feature_cols]
    y = merged_df[target_col]
    
    # Split the data
    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    logger.info("Data split into training and validation sets.")
    
    # Create an Optuna study
    study = optuna.create_study(direction='minimize', study_name='FantasyPointsOptimization')
    logger.info("Optuna study created.")
    
    # Optimize
    study.optimize(lambda trial: objective(trial, X_train, y_train, X_valid, y_valid, feature_cols), n_trials=50, timeout=1800)
    logger.info("Optuna study completed.")
    
    # Log best trial
    trial = study.best_trial
    logger.info("Best trial:")
    logger.info(f"  Value (MSE): {trial.value}")
    logger.info("  Params: ")
    for key, value in trial.params.items():
        logger.info(f"    {key}: {value}")
    
    # Recreate the best pipeline with the best parameters
    model_name = trial.params.pop('model')
    
    scaler = StandardScaler()
    poly = PolynomialFeatures(degree=2, include_bias=False)
    
    if model_name == 'RandomForest':
        regressor = RandomForestRegressor(
            n_estimators=trial.params['rf_n_estimators'],
            max_depth=trial.params['rf_max_depth'],
            min_samples_split=trial.params['rf_min_samples_split'],
            random_state=42
        )
    elif model_name == 'XGBoost':
        regressor = xgboost.XGBRegressor(
            n_estimators=trial.params['xgb_n_estimators'],
            max_depth=trial.params['xgb_max_depth'],
            learning_rate=trial.params['xgb_learning_rate'],
            subsample=trial.params['xgb_subsample'],
            objective='reg:squarederror',
            eval_metric='rmse',
            random_state=42,
            verbosity=0
        )
    elif model_name == 'LightGBM':
        regressor = lightgbm.LGBMRegressor(
            n_estimators=trial.params['lgbm_n_estimators'],
            max_depth=trial.params['lgbm_max_depth'],
            learning_rate=trial.params['lgbm_learning_rate'],
            num_leaves=trial.params['lgbm_num_leaves'],
            subsample=trial.params['lgbm_subsample'],
            random_state=42
        )
    
    # Create the best pipeline
    best_pipeline = Pipeline([
        ('scaler', scaler),
        ('poly_features', poly),
        ('regressor', regressor)
    ])
    
    # Train the best pipeline on the entire training data
    best_pipeline.fit(X_train, y_train)
    logger.info("Best pipeline trained on the entire training set.")
    
    # Evaluate on validation data
    y_pred = best_pipeline.predict(X_valid)
    mse = mean_squared_error(y_valid, y_pred)
    r2 = best_pipeline.score(X_valid, y_valid)
    logger.info(f"Best Pipeline Evaluation - MSE: {mse}, R²: {r2}")
    
    # Save the best pipeline
    model_save_path = Path('../data/processed/fantasy_pipeline.pkl')
    joblib.dump(best_pipeline, model_save_path)
    logger.info(f"Best pipeline saved at {model_save_path}")
    
    # Plot feature importances
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        if model_name == 'RandomForest' or model_name == 'LightGBM' or model_name == 'XGBoost':
            importances = best_pipeline.named_steps['regressor'].feature_importances_
            feature_names = best_pipeline.named_steps['poly_features'].get_feature_names_out(feature_cols)
            
            feature_importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importances
            }).sort_values(by='importance', ascending=False)
            
            plt.figure(figsize=(12, 8))
            sns.barplot(x='importance', y='feature', data=feature_importance_df.head(20))
            plt.title(f'Top 20 Feature Importances - {model_name}')
            plt.tight_layout()
            feature_importance_path = Path('../images/best_model_feature_importances.png')
            # plt.savefig(feature_importance_path)
            plt.close()
            logger.info(f"Feature importances plot saved at {feature_importance_path}")
    except Exception as e:
        logger.error(f"Error in plotting feature importances: {e}")

if __name__ == "__main__":
    main()