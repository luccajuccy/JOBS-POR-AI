"""
Database configuration for JobMatcher.
SQLite with async SQLAlchemy (aiosqlite).
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# --- Async engine (used by FastAPI app) ---
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./jobmatcher.db"

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --- Sync engine (used by populate.py and migrations) ---
SYNC_DATABASE_URL = "sqlite:///./jobmatcher.db"

sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


Base = declarative_base()


async def get_db():
    """Async dependency for FastAPI routes — yields an AsyncSession."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup (async)."""
    from models import (  # noqa: F401
        AdEvent,
        CandidateProfile,
        CompanyProfile,
        CrawlerLog,
        Job,
        Like,
        Match,
        Message,
        User,
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    os.makedirs("logs", exist_ok=True)


def init_db_sync():
    """Create all tables (sync, for populate.py)."""
    from models import (  # noqa: F401
        AdEvent,
        CandidateProfile,
        CompanyProfile,
        CrawlerLog,
        Job,
        Like,
        Match,
        Message,
        User,
    )
    Base.metadata.create_all(bind=sync_engine)
    os.makedirs("logs", exist_ok=True)
