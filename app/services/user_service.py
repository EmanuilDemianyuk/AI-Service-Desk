"""User service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import User, UserRole
from app.database.repositories import UserRepository
from app.exceptions import NotFoundError, ValidationError


class UserService:
    """Service for user operations."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def create_user(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None = None,
        role: UserRole = UserRole.APPLICANT,
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await self.repository.get_by_telegram_id(telegram_id)
        if existing_user:
            raise ValidationError(f"User with Telegram ID {telegram_id} already exists")

        user = await self.repository.create(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            role=role,
        )
        await self.repository.commit()
        return user

    async def get_user(self, user_id: int) -> User:
        """Get user by ID."""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        return await self.repository.get_by_telegram_id(telegram_id)

    async def get_or_create_user(
        self,
        telegram_id: int,
        full_name: str,
        username: str | None = None,
    ) -> User:
        """Get user or create if not exists. Superadmin gets ADMIN role automatically."""
        user = await self.repository.get_by_telegram_id(telegram_id)
        if user:
            return user

        role = UserRole.ADMIN if telegram_id == settings.superadmin_id else UserRole.APPLICANT
        return await self.create_user(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            role=role,
        )

    async def get_all_users(self) -> list[User]:
        """Get all users."""
        return await self.repository.get_all()

    async def get_all_executors(self) -> list[User]:
        """Get all executor users."""
        return await self.repository.get_all_executors()

    async def set_role(self, user_id: int, role: UserRole) -> User:
        """Change a user's role."""
        user = await self.get_user(user_id)
        user = await self.repository.update(user, role=role)
        await self.repository.commit()
        return user

    async def get_executor_for_type(self, task_type: str) -> User:
        """Get executor for task type."""
        # Get the first executor (simplified logic)
        # In a real app, you might have multiple executors per type
        executors = await self.repository.get_all_executors()
        if not executors:
            raise NotFoundError("No executors available")
        return executors[0]

    async def update_user(self, user_id: int, **kwargs) -> User:
        """Update user."""
        user = await self.get_user(user_id)
        user = await self.repository.update(user, **kwargs)
        await self.repository.commit()
        return user

    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate user."""
        return await self.update_user(user_id, is_active=False)

    async def activate_user(self, user_id: int) -> User:
        """Activate user."""
        return await self.update_user(user_id, is_active=True)
