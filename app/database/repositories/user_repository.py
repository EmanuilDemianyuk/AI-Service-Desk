"""User repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for User model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, **kwargs) -> User:
        """Create a new user."""
        user = User(**kwargs)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[User]:
        """Get all users."""
        result = await self.session.execute(select(User))
        return result.scalars().all()

    async def get_all_executors(self) -> list[User]:
        """Get all executor users."""
        from app.database.models import UserRole

        result = await self.session.execute(
            select(User).where(User.role == UserRole.EXECUTOR)
        )
        return result.scalars().all()

    async def update(self, user: User, **kwargs) -> User:
        """Update user."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.session.flush()
        return user

    async def delete(self, user: User) -> None:
        """Delete user."""
        await self.session.delete(user)
        await self.session.flush()

    async def commit(self) -> None:
        """Commit session."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback session."""
        await self.session.rollback()
