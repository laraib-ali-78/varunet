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


def get_db() -> Generator[Optional[Any], None, None]:
    """
    FastAPI dependency yielding database session/connection.
    """
    session = None
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        yield session
    except Exception:
        # If database service is offline in local dev/demo mode, yield None
        yield None
    finally:
        if session is not None and hasattr(session, "close"):
            session.close()
