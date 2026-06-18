"""User model."""

from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, Integer, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum

from app.database.base import Base


class UserRole(str, enum.Enum):
    """User roles."""

    APPLICANT = "APPLICANT"
    EXECUTOR = "EXECUTOR"
    ADMIN = "ADMIN"


class ExecutorType(str, enum.Enum):
    """Executor specialisation types. Only relevant for EXECUTOR role."""

    SYSADMIN = "SYSADMIN"
    MASTER = "MASTER"


class User(Base):
    """User model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.APPLICANT)
    type: Mapped[ExecutorType | None] = mapped_column(SQLEnum(ExecutorType), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    created_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="Task.applicant_id",
        back_populates="applicant",
        cascade="all, delete-orphan",
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="Task.executor_id",
        back_populates="executor",
    )

    def __repr__(self) -> str:
        return f"<User {self.id} {self.full_name} ({self.role})>"


# Import Task for type hints
from app.database.models.task import Task  # noqa: E402, F401
