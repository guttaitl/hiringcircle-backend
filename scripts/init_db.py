#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables based on SQLAlchemy models.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, check_db_connection
from core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize database."""
    logger.info("Initializing database...")
    
    try:
        # Check connection first
        if check_db_connection():
            logger.info("✓ Database connection successful")
        else:
            logger.error("✗ Database connection failed")
            return 1
        
        # Create tables
        init_db()
        logger.info("✓ Database tables created successfully")
        
        return 0
        
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
