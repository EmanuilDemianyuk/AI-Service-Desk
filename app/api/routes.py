"""API routers and endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_db_session
from app.database.repositories import TaskRepository, UserRepository
from app.exceptions import NotFoundError, ValidationError
from app.schemas import (
    HealthResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services import NotionSyncService, TaskService, UserService

# Create routers
router = APIRouter(prefix="/api", tags=["API"])
health_router = APIRouter(tags=["Health"])

# ── Dependency factories ───────────────────────────────────────────────────

DBSession = Annotated[AsyncSession, Depends(get_db_session)]


async def _get_user_service(session: DBSession) -> UserService:
    return UserService(UserRepository(session))


async def _get_task_service(session: DBSession) -> TaskService:
    return TaskService(TaskRepository(session), UserRepository(session), notion_sync=NotionSyncService())


UserServiceDep = Annotated[UserService, Depends(_get_user_service)]
TaskServiceDep = Annotated[TaskService, Depends(_get_task_service)]


# ── Health ─────────────────────────────────────────────────────────────────

@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy", message="Service is running")


# ── Users ──────────────────────────────────────────────────────────────────

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    user_service: UserServiceDep,
) -> UserResponse:
    """Create a new user with any role. EXECUTOR requires type=SYSADMIN|MASTER."""
    try:
        return await user_service.create_user(
            telegram_id=user_data.telegram_id,
            full_name=user_data.full_name,
            username=user_data.username,
            role=user_data.role,
            executor_type=user_data.type,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/users", response_model=list[UserResponse])
async def list_users(user_service: UserServiceDep) -> list[UserResponse]:
    """List all users."""
    return await user_service.get_all_users()


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    user_service: UserServiceDep,
) -> UserResponse:
    """Partially update a user. Only provided fields are changed.
    EXECUTOR role requires type=SYSADMIN|MASTER.
    Changing away from EXECUTOR automatically clears type.
    """
    try:
        return await user_service.update_user_fields(user_id, user_data)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ── Notion ─────────────────────────────────────────────────────────────────

@router.post("/notion/sync", status_code=status.HTTP_200_OK)
async def sync_notion(task_service: TaskServiceDep) -> dict:
    """Bulk-sync all DB tasks to Notion. DB is the authoritative source of truth."""
    return await task_service.sync_all_to_notion()


# ── Tasks ──────────────────────────────────────────────────────────────────

@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(task_service: TaskServiceDep) -> TaskListResponse:
    """Get all tasks."""
    tasks = await task_service.get_all_tasks()
    return TaskListResponse(items=tasks, total=len(tasks))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, task_service: TaskServiceDep) -> TaskResponse:
    """Get task by ID."""
    try:
        return await task_service.get_task(task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    task_service: TaskServiceDep,
) -> TaskResponse:
    """Create a new task."""
    return await task_service.create_task(
        applicant_id=task_data.applicant_id,
        title=task_data.title,
        description=task_data.description or "",
        task_type=task_data.type,
        priority=task_data.priority,
        executor_id=task_data.executor_id,
    )


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: int,
    task_update: TaskUpdate,
    task_service: TaskServiceDep,
) -> TaskResponse:
    """Update task status, feedback, or executor."""
    try:
        return await task_service.patch_task(
            task_id,
            status=task_update.status,
            feedback=task_update.feedback,
            executor_id=task_update.executor_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
