"""Dependency injection setup."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import AsyncSessionLocal
from app.database.repositories import UserRepository, TaskRepository
from app.services import UserService, TaskService, AIService, NotionService


async def get_user_service(session: AsyncSession) -> UserService:
    """Get user service."""
    repository = UserRepository(session)
    return UserService(repository)


async def get_task_service(
    session: AsyncSession,
) -> TaskService:
    """Get task service."""
    task_repository = TaskRepository(session)
    user_repository = UserRepository(session)
    return TaskService(task_repository, user_repository)


def get_ai_service() -> AIService:
    """Get AI service."""
    return AIService()


def get_notion_service() -> NotionService:
    """Get Notion service."""
    return NotionService()
