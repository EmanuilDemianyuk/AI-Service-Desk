"""Task service."""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Task, TaskStatus, TaskType, TaskPriority
from app.database.repositories import TaskRepository, UserRepository
from app.exceptions import NotFoundError


class TaskService:
    """Service for task operations."""

    def __init__(
        self,
        task_repository: TaskRepository,
        user_repository: UserRepository,
    ) -> None:
        self.task_repository = task_repository
        self.user_repository = user_repository

    async def create_task(
        self,
        applicant_id: int,
        title: str,
        description: str,
        task_type: TaskType,
        priority: TaskPriority,
        executor_id: int | None = None,
        notion_page_id: str | None = None,
    ) -> Task:
        """Create a new task."""
        task = await self.task_repository.create(
            applicant_id=applicant_id,
            executor_id=executor_id,
            title=title,
            description=description,
            type=task_type,
            priority=priority,
            status=TaskStatus.NEW,
            notion_page_id=notion_page_id,
        )
        await self.task_repository.commit()
        return task

    async def get_task(self, task_id: int) -> Task:
        """Get task by ID."""
        task = await self.task_repository.get_by_id(task_id)
        if not task:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def get_task_by_notion_id(self, notion_page_id: str) -> Task | None:
        """Get task by Notion page ID."""
        return await self.task_repository.get_by_notion_id(notion_page_id)

    async def get_user_tasks(self, user_id: int) -> list[Task]:
        """Get all tasks for a user (as applicant)."""
        return await self.task_repository.get_by_applicant(user_id)

    async def get_new_tasks(self) -> list[Task]:
        """Get all NEW tasks."""
        return await self.task_repository.get_new_tasks()

    async def get_executor_tasks(self, executor_id: int) -> list[Task]:
        """Get IN_PROGRESS and WAITING_EXECUTOR tasks for executor."""
        return await self.task_repository.get_executor_in_progress_tasks(executor_id)

    async def take_task(self, task_id: int, executor_id: int) -> Task:
        """Take task into progress."""
        task = await self.get_task(task_id)
        if task.status != TaskStatus.NEW:
            raise ValueError(f"Task {task_id} is not in NEW status")

        task = await self.task_repository.update(
            task,
            executor_id=executor_id,
            status=TaskStatus.IN_PROGRESS,
        )
        await self.task_repository.commit()
        return task

    async def complete_task(self, task_id: int, feedback: str) -> Task:
        """Complete task and request applicant confirmation."""
        task = await self.get_task(task_id)
        if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.WAITING_EXECUTOR]:
            raise ValueError(f"Task {task_id} cannot be completed in {task.status} status")

        task = await self.task_repository.update(
            task,
            status=TaskStatus.WAITING_APPLICANT,
            feedback=feedback,
        )
        await self.task_repository.commit()
        return task

    async def confirm_task(self, task_id: int) -> Task:
        """Confirm task completion by applicant."""
        task = await self.get_task(task_id)
        if task.status != TaskStatus.WAITING_APPLICANT:
            raise ValueError(f"Task {task_id} is not waiting for applicant confirmation")

        task = await self.task_repository.update(
            task,
            status=TaskStatus.DONE,
            closed_at=datetime.utcnow(),
        )
        await self.task_repository.commit()
        return task

    async def reject_task(self, task_id: int) -> Task:
        """Reject task completion by applicant."""
        task = await self.get_task(task_id)
        if task.status != TaskStatus.WAITING_APPLICANT:
            raise ValueError(f"Task {task_id} is not waiting for applicant confirmation")

        task = await self.task_repository.update(
            task,
            status=TaskStatus.WAITING_EXECUTOR,
        )
        await self.task_repository.commit()
        return task

    async def cancel_task(self, task_id: int) -> Task:
        """Cancel task."""
        task = await self.get_task(task_id)
        task = await self.task_repository.update(
            task,
            status=TaskStatus.CANCELLED,
            closed_at=datetime.utcnow(),
        )
        await self.task_repository.commit()
        return task

    async def update_notion_page_id(self, task_id: int, notion_page_id: str) -> Task:
        """Update Notion page ID for a task."""
        task = await self.get_task(task_id)
        task = await self.task_repository.update(
            task,
            notion_page_id=notion_page_id,
        )
        await self.task_repository.commit()
        return task

    async def update_task_status(self, task_id: int, status: TaskStatus) -> Task:
        """Update task status."""
        task = await self.get_task(task_id)
        task = await self.task_repository.update(task, status=status)
        await self.task_repository.commit()
        return task
