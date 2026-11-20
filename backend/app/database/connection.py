import asyncio
import logging
from typing import AsyncGenerator, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.exceptions import DatabaseNotConfiguredException

logger = logging.getLogger("flowstate.database")


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0 Declarative Base class.
    All future ORM models (Users, Workspaces, Projects, Tasks, etc.) will inherit from this class.
    """
    pass


# Global engine and sessionmaker instances
engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def init_database() -> Optional[AsyncEngine]:
    """
    Initializes or re-initializes the asynchronous database engine and sessionmaker.
    """
    global engine, async_session_factory

    if not settings.async_database_url:
        logger.info("DATABASE_URL not configured. Running in database-less mode.")
        engine = None
        async_session_factory = None
        return None

    try:
        engine = create_async_engine(
            settings.async_database_url,
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_pre_ping=True,
        )
        async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        logger.info("Asynchronous database engine initialized successfully.")
        return engine
    except Exception as e:
        logger.error("Failed to initialize database engine: %s", type(e).__name__)
        engine = None
        async_session_factory = None
        return None


# Initialize on module import
init_database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an asynchronous SQLAlchemy database session.
    Automatically handles commit on success, rollback on error, and session closure.
    """
    global async_session_factory
    if async_session_factory is None:
        init_database()
        if async_session_factory is None:
            raise DatabaseNotConfiguredException(
                "Database connection has not been configured yet. Set DATABASE_URL in .env to enable database operations."
            )

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection(timeout_seconds: float = 5.0) -> Tuple[bool, str, str]:
    """
    Verifies database connectivity by executing SELECT 1 with an asynchronous timeout.
    Safely handles errors without leaking credentials.

    Returns:
        Tuple of (is_connected: bool, database_status: str, details_message: str)
    """
    if not settings.async_database_url:
        return False, "unconfigured", "Database URL is not configured. Backend foundation is operational."

    active_engine = engine
    if active_engine is None:
        active_engine = init_database()
        if active_engine is None:
            return False, "unconfigured", "Database engine is not initialized."

    try:
        async with asyncio.timeout(timeout_seconds):
            async with active_engine.connect() as conn:
                # Execute lightweight verification query
                await conn.execute(text("SELECT 1"))
                return True, "connected", "Database connection verified successfully (SELECT 1 succeeded)."
    except TimeoutError:
        logger.warning("Database readiness probe timed out after %.1f seconds.", timeout_seconds)
        return False, "disconnected", f"Database connection attempt timed out after {timeout_seconds}s."
    except Exception as exc:
        logger.warning("Database readiness probe failed (connection attempt error: %s).", type(exc).__name__)
        return False, "disconnected", "Database connection could not be established."


async def close_database_connections() -> None:
    """Closes all active database pool connections during application shutdown."""
    global engine, async_session_factory
    if engine is not None:
        logger.info("Disposing database engine connection pool...")
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("Database connection pool disposed.")
