"""
Database Session Management for VaruNet
Provides database connections and dependency injection for FastAPI routers.
Supports SQLAlchemy Sessions with automatic psycopg2 failover.
"""

import os
import logging
from typing import Generator, Any, Optional

logger = logging.getLogger("varunet.db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/varunet"
)

sa_url = DATABASE_URL
if sa_url.startswith("postgres://"):
    sa_url = sa_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif sa_url.startswith("postgresql://") and not sa_url.startswith("postgresql+"):
    sa_url = sa_url.replace("postgresql://", "postgresql+psycopg2://", 1)

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(sa_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.warning("Could not initialize SQLAlchemy engine: %s. Using psycopg2 fallback.", str(e))
    engine = None
    SessionLocal = None


def get_db() -> Generator[Optional[Any], None, None]:
    """
    FastAPI dependency yielding database session/connection.
    """
    session = None
    try:
        if SessionLocal is not None:
            session = SessionLocal()
            yield session
        else:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            session = conn
            yield conn
    except Exception as e:
        logger.error("Database connection error in get_db: %s", str(e))
        # Final attempt: direct psycopg2 connection
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            session = conn
            yield conn
        except Exception as e2:
            logger.error("Final direct psycopg2 fallback failed: %s", str(e2))
            yield None
    finally:
        if session is not None and hasattr(session, "close"):
            session.close()
