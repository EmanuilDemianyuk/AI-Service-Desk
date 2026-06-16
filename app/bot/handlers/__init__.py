# Bot handlers
from app.bot.handlers.common import router as common_router
from app.bot.handlers.applicant import router as applicant_router
from app.bot.handlers.executor import router as executor_router

routers = [common_router, applicant_router, executor_router]

__all__ = [
    "common_router",
    "applicant_router",
    "executor_router",
    "routers",
]
