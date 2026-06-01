import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv

load_dotenv()

IS_IN_DOCKER = os.path.exists('/.dockerenv')

DEFAULT_POSTGRES_HOST = "postgres" if IS_IN_DOCKER else "localhost"

USER = os.getenv("POSTGRES_USER", "postgres")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "secret")
HOST = os.getenv("POSTGRES_HOST",  DEFAULT_POSTGRES_HOST)
PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "mydb")

DATABASE_URL = f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"

# Створення асинхронного рушія
engine = create_async_engine(DATABASE_URL, echo=True, connect_args={"statement_cache_size": 0})

# Фабрика сесій
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency для отримання сесії в ендпоінтах
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session