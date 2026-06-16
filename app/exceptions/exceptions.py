"""Custom application exceptions."""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class ValidationError(AppException):
    """Validation error exception."""

    pass


class NotFoundError(AppException):
    """Resource not found exception."""

    pass


class AuthenticationError(AppException):
    """Authentication error exception."""

    pass


class AuthorizationError(AppException):
    """Authorization error exception."""

    pass


class AIServiceError(AppException):
    """AI service error exception."""

    pass


class NotionServiceError(AppException):
    """Notion service error exception."""

    pass


class TelegramServiceError(AppException):
    """Telegram service error exception."""

    pass


class DatabaseError(AppException):
    """Database error exception."""

    pass
