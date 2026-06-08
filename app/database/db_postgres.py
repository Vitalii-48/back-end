from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Використовуємо async_database_url, який автоматично обере правильний варіант
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    connect_args={"statement_cache_size": 0}
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db_postgres():
    async with AsyncSessionLocal() as session:
        yield session