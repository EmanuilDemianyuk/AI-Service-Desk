"""Base repository class."""

from abc import ABC
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository(ABC):
    """Base repository for all repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
