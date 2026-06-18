"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from typing import Optional

from app.database.models import TaskStatus, TaskType, TaskPriority, UserRole, ExecutorType


class UserBase(BaseModel):
    """Base user schema."""

    full_name: str
    username: Optional[str] = None
    role: UserRole = UserRole.APPLICANT


class UserCreate(UserBase):
    """User creation schema."""

    telegram_id: int
    type: Optional[ExecutorType] = None

    @model_validator(mode="after")
    def validate_executor_type(self) -> "UserCreate":
        if self.role == UserRole.EXECUTOR and self.type is None:
            raise ValueError("type is required for EXECUTOR role (SYSADMIN or MASTER)")
        if self.role != UserRole.EXECUTOR and self.type is not None:
            raise ValueError("type must be null for non-EXECUTOR roles")
        return self


class UserUpdate(BaseModel):
    """User partial-update schema. All fields optional; only provided fields are changed."""

    full_name: Optional[str] = None
    username: Optional[str] = None
    telegram_id: Optional[int] = None
    role: Optional[UserRole] = None
    type: Optional[ExecutorType] = None

    @model_validator(mode="after")
    def validate_role_type(self) -> "UserUpdate":
        # When explicitly setting role=EXECUTOR, type must be provided in the same request
        if self.role == UserRole.EXECUTOR and self.type is None:
            raise ValueError("type is required when setting role to EXECUTOR (SYSADMIN or MASTER)")
        # When explicitly setting a non-EXECUTOR role, type must not be provided
        if self.role is not None and self.role != UserRole.EXECUTOR and self.type is not None:
            raise ValueError("type must be null for non-EXECUTOR roles")
        return self


class UserResponse(UserBase):
    """User response schema."""

    id: int
    telegram_id: int
    type: Optional[ExecutorType] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    """Base task schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: TaskType
    priority: TaskPriority


class TaskCreate(TaskBase):
    """Task creation schema."""

    applicant_id: int
    executor_id: Optional[int] = None


class TaskUpdate(BaseModel):
    """Task update schema."""

    status: Optional[TaskStatus] = None
    feedback: Optional[str] = None
    executor_id: Optional[int] = None


class TaskResponse(TaskBase):
    """Task response schema."""

    id: int
    applicant_id: int
    executor_id: Optional[int] = None
    status: TaskStatus
    feedback: Optional[str] = None
    created_at: datetime
    closed_at: Optional[datetime] = None
    notion_page_id: Optional[str] = None

    class Config:
        from_attributes = True


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
    detail: Optional[str] = None
    code: Optional[str] = None
