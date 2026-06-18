"""User service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import User, UserRole, ExecutorType
from app.database.repositories import UserRepository
from app.exceptions import NotFoundError, ValidationError, NoExecutorError
from app.schemas.schemas import UserUpdate


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
        executor_type: ExecutorType | None = None,
    ) -> User:
        """Create a new user."""
        existing_user = await self.repository.get_by_telegram_id(telegram_id)
        if existing_user:
            raise ValidationError(f"User with Telegram ID {telegram_id} already exists")

        if role == UserRole.EXECUTOR and executor_type is None:
            raise ValidationError("executor_type is required for EXECUTOR role")
        if role != UserRole.EXECUTOR and executor_type is not None:
            raise ValidationError("executor_type must be None for non-EXECUTOR roles")

        user = await self.repository.create(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            role=role,
            type=executor_type,
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
        """Return executor whose type matches the task type (SYSTEM→SYSADMIN, LOCAL→MASTER).

        Raises NoExecutorError if no executor of the required type exists.
        No fallback — executor selection is strict per business rules.
        """
        desired = ExecutorType.SYSADMIN if task_type == "SYSTEM" else ExecutorType.MASTER
        executors = await self.repository.get_executors_by_type(desired)
        if not executors:
            raise NoExecutorError(
                f"На жаль, наразі відсутній виконавець типу {desired.value}, "
                f"який може обробити цей тип запиту."
            )
        return executors[0]

    async def update_user_fields(self, user_id: int, data: UserUpdate) -> User:
        """Partially update a user. Validates role/type consistency against the current DB state."""
        user = await self.get_user(user_id)

        # Unique telegram_id check (skip if unchanged)
        if data.telegram_id is not None and data.telegram_id != user.telegram_id:
            conflict = await self.repository.get_by_telegram_id_excluding(
                data.telegram_id, exclude_user_id=user_id
            )
            if conflict:
                raise ValidationError(f"telegram_id {data.telegram_id} is already taken")

        # Resolve final role and type after merging with current DB values
        final_role = data.role if data.role is not None else user.role

        if data.type is not None:
            final_type: ExecutorType | None = data.type
        elif data.role is not None and data.role != UserRole.EXECUTOR:
            # Role is explicitly changing away from EXECUTOR — clear type
            final_type = None
        else:
            final_type = user.type

        # Final business-rule validation on merged state
        if final_role == UserRole.EXECUTOR and final_type is None:
            raise ValidationError("type is required for EXECUTOR role (SYSADMIN or MASTER)")
        if final_role != UserRole.EXECUTOR:
            final_type = None  # always clear type for non-executor roles

        update_kwargs: dict = {"role": final_role, "type": final_type}
        if data.full_name is not None:
            update_kwargs["full_name"] = data.full_name
        if data.username is not None:
            update_kwargs["username"] = data.username
        if data.telegram_id is not None:
            update_kwargs["telegram_id"] = data.telegram_id

        user = await self.repository.update(user, **update_kwargs)
        await self.repository.commit()
        return user

    async def update_user(self, user_id: int, **kwargs) -> User:
        """Update user."""
        user = await self.get_user(user_id)
        user = await self.repository.update(user, **kwargs)
        await self.repository.commit()
        return user

    async def delete_user(self, user_id: int) -> None:
        """Delete user. Cascades to their created tasks; clears executor_id on assigned tasks."""
        user = await self.get_user(user_id)
        await self.repository.delete(user)
        await self.repository.commit()

    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate user."""
        return await self.update_user(user_id, is_active=False)

    async def activate_user(self, user_id: int) -> User:
        """Activate user."""
        return await self.update_user(user_id, is_active=True)
