"""
database.py
============
Sets up the local SQLite database via SQLAlchemy. SQLite is a
serverless, zero-configuration, open-source database engine that ships
with Python - it needs no installation and no network service, which
keeps SAAMai fully self-contained and offline-capable.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables if they don't exist yet. Called once on startup."""
    from . import models  # noqa: F401  (import so models register on Base.metadata)

    Base.metadata.create_all(bind=engine)
