from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# Use SQLite for testing if PostgreSQL is not available
DATABASE_URL = settings.DATABASE_URL
if "postgresql" in DATABASE_URL and "+asyncpg" in DATABASE_URL:
    try:
        import asyncpg
    except ImportError:
        # Fallback to SQLite for testing
        DATABASE_URL = "sqlite+aiosqlite:///./smart_menu_test.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    import logging
    logger = logging.getLogger(__name__)
    async with AsyncSessionLocal() as session:
        logger.info("Database session created")
        try:
            yield session
        finally:
            logger.info("Database session closing")
            await session.close()
            logger.info("Database session closed")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()