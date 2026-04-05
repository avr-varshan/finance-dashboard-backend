from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


# Force asyncpg driver if user accidentally puts normal postgres URL
database_url = settings.database_url.replace(
    "postgresql://",
    "postgresql+asyncpg://"
)

engine: AsyncEngine = create_async_engine(
    database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "statement_cache_size": 0
    }
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session