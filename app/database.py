"""
app/database.py
SQLAlchemy 2.0 engine and session setup.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

engine = create_engine(
    settings.database_url,
    # Echo SQL to stdout in debug mode – helpful for students.
    echo=settings.debug,
    pool_pre_ping=True,   # Test connections before using them.
    pool_size=10,
    max_overflow=20,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """All ORM models must inherit from this class."""
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency – yields a session and guarantees cleanup
# ---------------------------------------------------------------------------

def get_db():
    """Yield a database session; always close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Startup health check
# ---------------------------------------------------------------------------

def check_db_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
