"""
Database initialization and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
from .models import Base


def init_db():
    """Initialize database, create tables if they don't exist."""
    engine = create_engine(settings.database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


# Create engine and session factory
engine = init_db()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


def close_db():
    """Close all database connections."""
    engine.dispose()
