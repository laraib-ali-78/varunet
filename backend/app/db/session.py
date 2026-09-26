"""
Database Session Management for VaruNet
Provides database connections and dependency injection for FastAPI routers.
"""

import os
from typing import Generator, Any, Optional

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/varunet"
)


try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception:
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
    except Exception:
        yield None
    finally:
        if session is not None and hasattr(session, "close"):
            session.close()
