"""Telegram bot setup and initialization."""

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import settings
from app.bot.handlers import routers


async def setup_default_commands(bot: Bot) -> None:
    """Setup default bot commands."""
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="Show help"),
        BotCommand(command="cancel", description="Cancel current operation"),
    ]
    await bot.set_my_commands(commands)


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Setup and initialize the bot."""
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register routers
    for router in routers:
        dp.include_router(router)

    # Setup default commands
    await setup_default_commands(bot)

    return bot, dp
