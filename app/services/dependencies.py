"""Dependency injection setup."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import AsyncSessionLocal
from app.database.repositories import UserRepository, TaskRepository
from app.services import UserService, TaskService, AIService, NotionService, NotionSyncService


async def get_user_service(session: AsyncSession) -> UserService:
    """Get user service."""
    repository = UserRepository(session)
    return UserService(repository)


async def get_task_service(
    session: AsyncSession,
    with_notion_sync: bool = True,
) -> TaskService:
    """Get task service, optionally wired with NotionSyncService."""
    task_repository = TaskRepository(session)
    user_repository = UserRepository(session)
    notion_sync = NotionSyncService() if with_notion_sync else None
    return TaskService(task_repository, user_repository, notion_sync=notion_sync)


def get_ai_service() -> AIService:
    """Get AI service."""
    return AIService()


def get_notion_service() -> NotionService:
    """Get Notion service (legacy — prefer NotionSyncService for new code)."""
    return NotionService()


def get_notion_sync_service() -> NotionSyncService:
    """Get Notion sync service."""
    return NotionSyncService()
