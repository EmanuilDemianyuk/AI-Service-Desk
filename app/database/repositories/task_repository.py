"""Task repository."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Task, TaskStatus, TaskType
from app.database.repositories.base import BaseRepository


class TaskRepository(BaseRepository):
    """Repository for Task model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create(self, **kwargs) -> Task:
        """Create a new task."""
        task = Task(**kwargs)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        """Get task by ID."""
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def get_by_id_with_relations(self, task_id: int) -> Task | None:
        """Get task by ID with applicant and executor eagerly loaded."""
        result = await self.session.execute(
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.applicant), selectinload(Task.executor))
        )
        return result.scalar_one_or_none()

    async def get_by_notion_id(self, notion_page_id: str) -> Task | None:
        """Get task by Notion page ID."""
        result = await self.session.execute(
            select(Task).where(Task.notion_page_id == notion_page_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Task]:
        """Get all tasks."""
        result = await self.session.execute(select(Task))
        return result.scalars().all()

    async def get_all_with_relations(self) -> list[Task]:
        """Get all tasks with applicant and executor eagerly loaded."""
        result = await self.session.execute(
            select(Task).options(selectinload(Task.applicant), selectinload(Task.executor))
        )
        return result.scalars().all()

    async def get_by_applicant(self, applicant_id: int) -> list[Task]:
        """Get all tasks for an applicant."""
        result = await self.session.execute(
            select(Task).where(Task.applicant_id == applicant_id)
        )
        return result.scalars().all()

    async def get_by_executor(self, executor_id: int) -> list[Task]:
        """Get all tasks for an executor."""
        result = await self.session.execute(
            select(Task).where(Task.executor_id == executor_id)
        )
        return result.scalars().all()

    async def get_by_status(self, status: TaskStatus) -> list[Task]:
        """Get all tasks with a specific status."""
        result = await self.session.execute(select(Task).where(Task.status == status))
        return result.scalars().all()

    async def get_new_tasks(self) -> list[Task]:
        """Get all NEW tasks."""
        result = await self.session.execute(
            select(Task).where(Task.status == TaskStatus.NEW)
        )
        return result.scalars().all()

    async def get_new_tasks_for_executor_type(self, task_type: TaskType) -> list[Task]:
        """Get NEW tasks filtered by task type (SYSTEM for SYSADMIN, LOCAL for MASTER)."""
        result = await self.session.execute(
            select(Task).where(
                (Task.status == TaskStatus.NEW) & (Task.type == task_type)
            )
        )
        return result.scalars().all()

    async def get_waiting_for_applicant(self, applicant_id: int) -> list[Task]:
        """Get WAITING_APPLICANT tasks for a given applicant."""
        result = await self.session.execute(
            select(Task).where(
                (Task.applicant_id == applicant_id)
                & (Task.status == TaskStatus.WAITING_APPLICANT)
            )
        )
        return result.scalars().all()

    async def get_executor_in_progress_tasks(self, executor_id: int) -> list[Task]:
        """Get IN_PROGRESS and WAITING_EXECUTOR tasks for an executor."""
        result = await self.session.execute(
            select(Task).where(
                (Task.executor_id == executor_id)
                & (
                    (Task.status == TaskStatus.IN_PROGRESS)
                    | (Task.status == TaskStatus.WAITING_EXECUTOR)
                )
            )
        )
        return result.scalars().all()

    async def update(self, task: Task, **kwargs) -> Task:
        """Update task."""
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        await self.session.flush()
        return task

    async def delete(self, task: Task) -> None:
        """Delete task."""
        await self.session.delete(task)
        await self.session.flush()

    async def commit(self) -> None:
        """Commit session."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback session."""
        await self.session.rollback()
