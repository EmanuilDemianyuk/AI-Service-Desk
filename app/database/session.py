"""Database session management."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import AsyncSessionLocal


async def get_session() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session
