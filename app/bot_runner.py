"""Bot runner for polling."""

import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.bot import setup_bot
from app.database.base import AsyncSessionLocal
from app.database.repositories import UserRepository, TaskRepository
from app.services import (
    UserService,
    TaskService,
    AIService,
    NotionService,
)
from app.core import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def main() -> None:
    """Main bot runner."""
    logger.info("🤖 Starting Telegram bot...")

    # Setup bot
    bot, dp = await setup_bot()

    # Create services
    async with AsyncSessionLocal() as session:
        user_repository = UserRepository(session)
        task_repository = TaskRepository(session)
        user_service = UserService(user_repository)
        task_service = TaskService(task_repository, user_repository)
        ai_service = AIService()
        notion_service = NotionService()

        # Inject dependencies
        dp.workflow_data.update(
            {
                "user_service": user_service,
                "task_service": task_service,
                "ai_service": ai_service,
                "notion_service": notion_service,
            }
        )

    try:
        logger.info("🎯 Bot polling started")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
    finally:
        logger.info("🛑 Bot stopped")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
