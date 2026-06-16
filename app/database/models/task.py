"""Task model."""

from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum

from app.database.base import Base


class TaskStatus(str, enum.Enum):
    """Task statuses."""

    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPLICANT = "WAITING_APPLICANT"
    WAITING_EXECUTOR = "WAITING_EXECUTOR"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskType(str, enum.Enum):
    """Task types."""

    SYSTEM = "SYSTEM"
    LOCAL = "LOCAL"


class TaskPriority(str, enum.Enum):
    """Task priorities."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Task(Base):
    """Task model."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notion_page_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    applicant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    executor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType), nullable=False)
    priority: Mapped[TaskPriority] = mapped_column(SQLEnum(TaskPriority), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus),
        default=TaskStatus.NEW,
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    applicant: Mapped["User"] = relationship(
        "User",
        foreign_keys=[applicant_id],
        back_populates="created_tasks",
    )
    executor: Mapped["User"] = relationship(
        "User",
        foreign_keys=[executor_id],
        back_populates="assigned_tasks",
    )

    def __repr__(self) -> str:
        return f"<Task {self.id} {self.title} ({self.status})>"


# Import User for type hints
from app.database.models.user import User  # noqa: E402, F401
