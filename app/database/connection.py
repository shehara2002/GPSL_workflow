from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# SQLAlchemy engine configuration with psycopg 3 driver and connection pooling
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,  # Automatically verify connections and reconnect if dropped
    pool_size=10,
    max_overflow=20,
)

# Session factory for handling database transactions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for SQLAlchemy ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request,
    ensuring the session is cleanly closed when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> dict:
    """
    Tests database connectivity and returns connection details or error info.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            val = result.scalar()
            return {
                "status": "connected",
                "database": engine.url.database,
                "host": engine.url.host,
                "port": engine.url.port,
                "driver": engine.url.drivername,
                "test_query_result": val
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }