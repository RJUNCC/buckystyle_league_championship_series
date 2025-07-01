# File: discord_bot/models/database_config.py

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import urllib.parse

logger = logging.getLogger(__name__)

# Base for all models
Base = declarative_base()

class DatabaseConfig:
    def __init__(self):
        self.engine = None
        self.Session = None
        self.database_url = None
    
    def get_database_url(self):
        """Get PostgreSQL database URL from environment variables"""
        
        # Option 1: Full DATABASE_URL (most common for DigitalOcean)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            # Handle both postgres:// and postgresql:// prefixes
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            return database_url
        
        # Option 2: Individual components (if you prefer separate env vars)
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT', '25060')  # Default DigitalOcean port
        db_name = os.getenv('DB_NAME')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        
        if all([db_host, db_name, db_user, db_password]):
            # URL encode password to handle special characters
            encoded_password = urllib.parse.quote_plus(db_password)
            return f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}?sslmode=require"
        
        # Option 3: Fallback to SQLite for local development
        logger.warning("⚠️ No PostgreSQL config found, falling back to SQLite")
        return "sqlite:///local_development.db"
    
    def initialize_database(self):
        """Initialize PostgreSQL database connection"""
        try:
            self.database_url = self.get_database_url()
            
            # Database engine configuration
            if self.database_url.startswith('postgresql://'):
                # PostgreSQL configuration for production
                self.engine = create_engine(
                    self.database_url,
                    poolclass=QueuePool,
                    pool_size=5,          # Number of connections to maintain
                    max_overflow=10,      # Additional connections if needed
                    pool_recycle=3600,    # Recycle connections every hour
                    pool_pre_ping=True,   # Validate connections before use
                    echo=False,           # Set to True for SQL debugging
                    connect_args={
                        "sslmode": "require",
                        "connect_timeout": 10,
                        "application_name": "RocketLeagueBot"
                    }
                )
                logger.info("✅ Configured PostgreSQL database engine")
            else:
                # SQLite configuration for local development
                self.engine = create_engine(
                    self.database_url,
                    echo=False,
                    connect_args={"check_same_thread": False}
                )
                logger.info("✅ Configured SQLite database engine (development)")
            
            # Create session factory
            self.Session = sessionmaker(bind=self.engine)
            
            # Test connection
            self.test_connection()
            
            # Create all tables
            self.create_tables()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise e
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                if result[0] == 1:
                    logger.info("✅ Database connection successful")
                    
                    # Log database info
                    if self.database_url.startswith('postgresql://'):
                        # Get PostgreSQL version
                        try:
                            version_result = conn.execute(text("SELECT version()")).fetchone()
                            logger.info(f"📊 PostgreSQL Version: {version_result[0][:50]}...")
                        except:
                            pass
                    
                    return True
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            raise e
    
    def create_tables(self):
        """Create all database tables"""
        try:
            # Import all models to ensure they're registered
            from models.player_profile import PlayerProfile
            from models.scheduling import SchedulingSession as DBSchedulingSession
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            logger.info("✅ Database tables created/verified")
            
            # Log existing tables
            try:
                with self.engine.connect() as conn:
                    if self.database_url.startswith('postgresql://'):
                        tables_result = conn.execute(text("""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public'
                            ORDER BY table_name
                        """)).fetchall()
                        table_names = [row[0] for row in tables_result]
                    else:
                        tables_result = conn.execute(text("""
                            SELECT name 
                            FROM sqlite_master 
                            WHERE type='table'
                            ORDER BY name
                        """)).fetchall()
                        table_names = [row[0] for row in tables_result]
                    
                    logger.info(f"📋 Tables in database: {', '.join(table_names)}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not list tables: {e}")
                
        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
            raise e
    
    def get_session(self):
        """Get a new database session"""
        if not self.Session:
            raise RuntimeError("Database not initialized. Call initialize_database() first.")
        return self.Session()
    
    def close_session(self, session):
        """Safely close a database session"""
        try:
            session.close()
        except Exception as e:
            logger.warning(f"⚠️ Error closing session: {e}")

# Global database configuration instance
db_config = DatabaseConfig()

# Convenience functions for backward compatibility
def initialize_database():
    """Initialize the database - main entry point"""
    return db_config.initialize_database()

def get_session():
    """Get a database session"""
    return db_config.get_session()

def get_engine():
    """Get the database engine"""
    return db_config.engine

# Export for use in other modules
engine = None
Session = None

def setup_database():
    """Setup database and export global variables"""
    global engine, Session
    db_config.initialize_database()
    engine = db_config.engine
    Session = db_config.Session
    return engine, Session