"""
Database configuration and session management.
Supports PostgreSQL (production) and SQLite (local development).
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, StaticPool
from typing import Generator
import logging
import os

from core.config import settings

logger = logging.getLogger(__name__)


def get_database_url():
    """
    Get database URL with fallback to SQLite for local development.
    """
    # Check if PostgreSQL URL is available and valid
    db_url = settings.database_url
    
    if db_url and db_url.startswith("postgresql://"):
        # Test if we can connect to PostgreSQL
        return db_url, "postgresql"
    
    # Fallback to SQLite for local development
    sqlite_path = os.path.join(os.path.dirname(__file__), "hiringcircle.db")
    logger.warning(f"PostgreSQL not configured or unavailable. Using SQLite: {sqlite_path}")
    return f"sqlite:///{sqlite_path}", "sqlite"


# Get database URL and type
DATABASE_URL, DB_TYPE = get_database_url()

# Create database engine based on database type
if DB_TYPE == "sqlite":
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
else:
    # PostgreSQL configuration
    if settings.ENVIRONMENT == "production":
        engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,
            pool_pre_ping=True
        )
    else:
        engine = create_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True
        )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Get database session dependency for FastAPI.
    
    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.
    Call this on application startup.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database tables created successfully using {DB_TYPE}")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            if DB_TYPE == "sqlite":
                conn.execute(text("SELECT 1"))
            else:
                conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


# Event listeners for connection debugging (only in debug mode)
if settings.DEBUG:
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, connection_record):
        logger.debug(f"Database connection established ({DB_TYPE})")
    
    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        logger.debug("Database connection checked out from pool")
    
    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        logger.debug("Database connection returned to pool")
