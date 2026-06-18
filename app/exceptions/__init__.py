# Application exceptions module

from app.exceptions.exceptions import (
    AppException,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    AIServiceError,
    NotionServiceError,
    TelegramServiceError,
    NoExecutorError,
)

__all__ = [
    "AppException",
    "ValidationError",
    "NotFoundError",
    "AuthenticationError",
    "AuthorizationError",
    "AIServiceError",
    "NotionServiceError",
    "TelegramServiceError",
    "NoExecutorError",
]
