"""Database session management and configuration."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url

        # Create async engine for CockroachDB with asyncpg
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL query logging
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("DatabaseManager initialized")

    async def create_tables(self):
        """Create all tables in the database."""
        logger.info("Creating database tables...")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    async def drop_tables(self):
        """Drop all tables in the database (use with caution!)."""
        logger.warning("Dropping all database tables...")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.

        Yields:
            AsyncSession: Database session
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()

    async def close(self):
        """Close the database connection pool."""
        logger.info("Closing database connection pool...")
        await self.engine.dispose()
        logger.info("Database connection pool closed")


# Global database manager instance
_db_manager: DatabaseManager | None = None


def init_db(database_url: str) -> DatabaseManager:
    """
    Initialize the global database manager.

    Args:
        database_url: Database connection URL

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


def get_db() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database manager is not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call init_db() first.")
    return _db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection helper for getting database sessions.

    Yields:
        AsyncSession: Database session
    """
    db = get_db()
    async with db.session() as session:
        yield session
