from sqlalchemy import create_engine, text
import pandas as pd
import os

def show_database_info():
    db_url = os.getenv('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(db_url)
    
    # Show all tables
    tables_query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    """
    tables_df = pd.read_sql(tables_query, engine)
    print("Tables in database:")
    print(tables_df)
    
    # Show columns for each table
    for table in tables_df['table_name']:
        columns_query = f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        """
        columns_df = pd.read_sql(columns_query, engine)
        print(f"\nColumns in {table}:")
        print(columns_df)
    

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    show_database_info()