"""Telegram bot setup and initialization."""

from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import settings
from app.bot.handlers import routers
from app.bot.middleware import CommandGuardMiddleware, DbSessionMiddleware, NavDeleteMiddleware


async def setup_default_commands(bot: Bot) -> None:
    """Setup default bot commands."""
    commands = [
        BotCommand(command="start", description="Запустити бота"),
        BotCommand(command="help", description="Показати довідку"),
        BotCommand(command="cancel", description="Скасувати поточну операцію"),
    ]
    await bot.set_my_commands(commands)


async def setup_bot() -> tuple[Bot, Dispatcher]:
    """Setup and initialize the bot."""
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Middleware chain (outermost → innermost, i.e. first registered runs first):
    #   1. DbSession  — opens a fresh DB session + injects services for every update.
    #   2. CommandGuard — blocks flow interrupts (needs services already in data).
    #   3. NavDelete  — deletes navigation button messages to keep the chat clean.
    db_middleware = DbSessionMiddleware()
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)
    dp.message.middleware(CommandGuardMiddleware())
    dp.message.middleware(NavDeleteMiddleware())

    # Register routers
    for router in routers:
        dp.include_router(router)

    # Setup default commands
    await setup_default_commands(bot)

    return bot, dp
