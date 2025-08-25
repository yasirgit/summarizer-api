"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.settings import get_settings

settings = get_settings()

# Synchronous engine for migrations
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,  # Enable SQLAlchemy 2.x features
)

# Asynchronous engine for async operations
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_recycle=300,
    future=True,  # Enable SQLAlchemy 2.x features
)

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def get_db():
    """Get synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection():
    """Check database connection."""
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_tables():
    """Create all tables (synchronous version for migrations)."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables (synchronous version for migrations)."""
    Base.metadata.drop_all(bind=engine)
