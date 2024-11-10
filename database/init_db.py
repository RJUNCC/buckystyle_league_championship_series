# database/init_db.py
import psycopg2
from psycopg2 import sql
from config.config import Config

def initialize_database():
    conn = psycopg2.connect(Config.DATABASE_URL)
    cursor = conn.cursor()
    
    with open('schema.sql', 'r') as f:
        cursor.execute(f.read())
    
    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    initialize_database()
