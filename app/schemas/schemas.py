"""Pydantic schemas for API requests and responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.database.models import ExecutorType, TaskPriority, TaskStatus, TaskType, UserRole


class UserBase(BaseModel):
    """Base user schema."""

    full_name: str
    username: str | None = None
    role: UserRole = UserRole.APPLICANT


class UserCreate(UserBase):
    """User creation schema."""

    telegram_id: int
    type: ExecutorType | None = None

    @model_validator(mode="after")
    def validate_executor_type(self) -> "UserCreate":
        if self.role == UserRole.EXECUTOR and self.type is None:
            raise ValueError("type is required for EXECUTOR role (SYSADMIN or MASTER)")
        if self.role != UserRole.EXECUTOR and self.type is not None:
            raise ValueError("type must be null for non-EXECUTOR roles")
        return self


class UserUpdate(BaseModel):
    """User partial-update schema. All fields optional; only provided fields are changed."""

    full_name: str | None = None
    username: str | None = None
    telegram_id: int | None = None
    role: UserRole | None = None
    type: ExecutorType | None = None

    @model_validator(mode="after")
    def validate_role_type(self) -> "UserUpdate":
        if self.role == UserRole.EXECUTOR and self.type is None:
            raise ValueError("type is required when setting role to EXECUTOR (SYSADMIN or MASTER)")
        if self.role is not None and self.role != UserRole.EXECUTOR and self.type is not None:
            raise ValueError("type must be null for non-EXECUTOR roles")
        return self


class UserResponse(UserBase):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    type: ExecutorType | None = None
    is_active: bool
    created_at: datetime


class TaskBase(BaseModel):
    """Base task schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    type: TaskType
    priority: TaskPriority


class TaskCreate(TaskBase):
    """Task creation schema."""

    applicant_id: int
    executor_id: int | None = None


class TaskUpdate(BaseModel):
    """Task update schema."""

    status: TaskStatus | None = None
    feedback: str | None = None
    executor_id: int | None = None


class TaskResponse(TaskBase):
    """Task response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    applicant_id: int
    executor_id: int | None = None
    status: TaskStatus
    feedback: str | None = None
    created_at: datetime
    closed_at: datetime | None = None
    notion_page_id: str | None = None


class TaskListResponse(BaseModel):
    """Task list response schema."""

    items: list[TaskResponse]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    message: str = "Service is running"


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str
    detail: str | None = None
    code: str | None = None
