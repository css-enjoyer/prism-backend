from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# Connection pool, provides a factory for creating and managing new database sessions
engine = create_async_engine(settings.database_url, echo=True)

# Session factory, for creating new asynchronous database sessions. It binds to the engine and specifies that sessions should not expire on commit.
AsyncSessionLocal = async_sessionmaker(
  bind=engine,
  class_=AsyncSession,
  expire_on_commit=False,
)

# Dependency function that provides a database session to the caller. It uses an asynchronous context manager to ensure that the session is properly closed after use, yielding the session for use in database operations.
async def get_db():
    async with AsyncSessionLocal() as session:
      yield session         # paused here — route handler runs
                            # route handler finishes
                            # resumed here — async with block closes the session