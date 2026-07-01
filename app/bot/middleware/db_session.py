"""Middleware that creates a fresh DB session and services per update."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.database.base import AsyncSessionLocal
from app.database.repositories import TaskRepository, UserRepository
from app.services import NotionSyncService, TaskService, UserService


class DbSessionMiddleware(BaseMiddleware):
    """Injects a per-request DB session and freshly constructed services into handler data.

    Each incoming update (message or callback) gets its own AsyncSession so that
    concurrent handlers never share the same SQLAlchemy session object.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionLocal() as session:
            user_repo = UserRepository(session)
            task_repo = TaskRepository(session)
            data["user_service"] = UserService(user_repo)
            data["task_service"] = TaskService(
                task_repo,
                user_repo,
                notion_sync=NotionSyncService(),
            )
            return await handler(event, data)
