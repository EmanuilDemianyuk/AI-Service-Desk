"""Bot runner for polling."""

import asyncio

from app.bot import setup_bot
from app.core import get_logger, setup_logging
from app.services import AIService, NotionService

setup_logging()
logger = get_logger(__name__)


async def main() -> None:
    """Main bot runner."""
    logger.info("🤖 Starting Telegram bot...")

    bot, dp = await setup_bot()

    # Singleton services that carry no DB session — safe to share across all updates.
    # Per-request UserService / TaskService are injected by DbSessionMiddleware.
    dp.workflow_data["ai_service"] = AIService()
    dp.workflow_data["notion_service"] = NotionService()

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
