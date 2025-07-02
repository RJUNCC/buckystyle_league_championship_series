
# discord_bot/migrations.py
import os
from sqlalchemy import create_engine, text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables with a fallback for local dev."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.warning("DATABASE_URL environment variable not found. Please ensure it is set for production.")
        # Provide a default for local testing if needed, but production should use env vars.
        return None 
        
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    return database_url

def apply_migration():
    """
    Connects to the database and applies the necessary schema changes.
    This script is idempotent, meaning it can be run multiple times without causing errors.
    """
    db_url = get_database_url()
    if not db_url:
        logger.error("Cannot run migration: DATABASE_URL is not set.")
        return

    logger.info(f"Connecting to database at {db_url.split('@')[-1]}...")
    
    try:
        engine = create_engine(db_url)
        
        # The SQL command to add all potentially missing columns and correct the discord_id type.
        # "IF NOT EXISTS" prevents errors if the columns already exist.
        sql_command = text("""
        ALTER TABLE player_profiles
        ADD COLUMN IF NOT EXISTS avg_speed REAL DEFAULT 0.0,
        ADD COLUMN IF NOT EXISTS dominance_quotient REAL DEFAULT 50.0,
        ADD COLUMN IF NOT EXISTS percentile_rank REAL DEFAULT 50.0,
        ADD COLUMN IF NOT EXISTS last_sync_date TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS last_game_date TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT true,
        ADD COLUMN IF NOT EXISTS extra_data JSONB,
        ALTER COLUMN discord_id TYPE BIGINT USING discord_id::BIGINT;

        ALTER TABLE scheduling_sessions
        ADD COLUMN IF NOT EXISTS proposed_times JSON DEFAULT '[]';
        """)

        with engine.connect() as connection:
            # Begin a transaction
            with connection.begin() as transaction:
                try:
                    logger.info("Executing ALTER TABLE command...")
                    connection.execute(sql_command)
                    transaction.commit()
                    logger.info("Migration successful: Columns avg_speed, dominance_quotient, percentile_rank, and proposed_times are present in their respective tables.")
                except Exception as e:
                    logger.error(f"❌ An error occurred during the transaction: {e}")
                    transaction.rollback()

    except Exception as e:
        logger.error(f"❌ Migration failed: Could not connect to the database or execute command. Error: {e}")

if __name__ == "__main__":
    logger.info("Starting database migration script...")
    apply_migration()
    logger.info("Migration script finished.")
