from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
from app.core.config import settings  # Adjust import to your settings location

# Use DATABASE_URL from settings
DATABASE_URL = settings.DATABASE_URL

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create async session maker
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession  )

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

