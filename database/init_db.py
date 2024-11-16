# database/init_db.py
import psycopg2
from config.config import Config
from pathlib import Path
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_database():
    try:
        config = Config()
        logging.info("Connecting to the PostgreSQL database...")

        # Establish the connection using psycopg2
        connection = psycopg2.connect(
            database=config.database_name,
            user=config.database_user,
            password=config.database_password,
            host=config.database_host,
            port=config.database_port
        )

        connection.autocommit = True
        cursor = connection.cursor()
        logging.info("Connected to the database successfully.")

        # Define the path to schema.sql
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            logging.error(f"Schema file not found at {schema_path}")
            sys.exit(1)

        # Read and execute schema.sql
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            cursor.execute(schema_sql)
            logging.info("Executed schema.sql successfully.")

        # Close the cursor and connection
        cursor.close()
        connection.close()
        logging.info("Database initialization completed successfully.")

    except psycopg2.Error as e:
        logging.error(f"Database connection failed: {e}")
        sys.exit(1)
    except EnvironmentError as e:
        logging.error(e)
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    initialize_database()
