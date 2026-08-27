"""
database.py
SQLAlchemy engine, session factory, and declarative base for PostgreSQL.
Provides the `get_db` FastAPI dependency used by all routers.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from api.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # recycle dead connections instead of erroring
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and ensures it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables from models. Intended for local dev / first run only —
    use Alembic migrations for anything beyond initial setup.
    """
    # Import models here so they register with Base.metadata before create_all
    from api.models import user, paper, query_log  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created (or already exist)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()