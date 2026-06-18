"""API routers and endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_db_session
from app.database.repositories import UserRepository, TaskRepository
from app.services import UserService, TaskService
from app.schemas import (
    HealthResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
    TaskResponse,
    TaskCreate,
    TaskUpdate,
    TaskListResponse,
)

# Create routers
router = APIRouter(prefix="/api", tags=["API"])
health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        message="Service is running",
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Create a new user with any role. EXECUTOR requires type=SYSADMIN|MASTER."""
    user_repository = UserRepository(session)
    user_service = UserService(user_repository)
    try:
        user = await user_service.create_user(
            telegram_id=user_data.telegram_id,
            full_name=user_data.full_name,
            username=user_data.username,
            role=user_data.role,
            executor_type=user_data.type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    """List all users."""
    user_repository = UserRepository(session)
    user_service = UserService(user_repository)
    return await user_service.get_all_users()


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Partially update a user. Only provided fields are changed.
    EXECUTOR role requires type=SYSADMIN|MASTER.
    Changing away from EXECUTOR automatically clears type.
    """
    user_repository = UserRepository(session)
    user_service = UserService(user_repository)
    try:
        user = await user_service.update_user_fields(user_id, user_data)
    except Exception as exc:
        from app.exceptions import NotFoundError
        status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return user


@router.get("/tasks", response_model=TaskListResponse)
async def get_tasks(
    session: AsyncSession = Depends(get_db_session),
) -> TaskListResponse:
    """Get all tasks."""
    task_repository = TaskRepository(session)
    tasks = await task_repository.get_all()
    return TaskListResponse(items=tasks, total=len(tasks))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Get task by ID."""
    task_repository = TaskRepository(session)
    task = await task_repository.get_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Create a new task."""
    task_repository = TaskRepository(session)
    task = await task_repository.create(**task_data.model_dump())
    await task_repository.commit()
    return task


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: int,
    task_update: TaskUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Update task status."""
    task_repository = TaskRepository(session)
    task = await task_repository.get_by_id(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = {}
    if task_update.status:
        update_data["status"] = task_update.status
    if task_update.feedback:
        update_data["feedback"] = task_update.feedback
    if task_update.executor_id:
        update_data["executor_id"] = task_update.executor_id

    task = await task_repository.update(task, **update_data)
    await task_repository.commit()
    return task
