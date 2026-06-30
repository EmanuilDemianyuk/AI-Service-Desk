"""Task service."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database.models import Task, TaskStatus, TaskType, TaskPriority
from app.database.repositories import TaskRepository, UserRepository
from app.exceptions import NotFoundError

logger = get_logger(__name__)


class TaskService:
    """Service for task operations. DB is the single source of truth.

    After every successful commit, a non-blocking Notion sync is attempted
    via `notion_sync` (if injected). Notion errors are logged but never
    propagated — they never rollback DB transactions.
    """

    def __init__(
        self,
        task_repository: TaskRepository,
        user_repository: UserRepository,
        notion_sync: "NotionSyncService | None" = None,  # noqa: F821
    ) -> None:
        self.task_repository = task_repository
        self.user_repository = user_repository
        self.notion_sync = notion_sync

    # ── Notion helpers ─────────────────────────────────────────────────────

    async def _notion_create(self, task: Task) -> None:
        """After create-commit: sync to Notion and persist the page_id."""
        if not self.notion_sync:
            return
        try:
            task_rel = await self.task_repository.get_by_id_with_relations(task.id)
            if task_rel is None:
                return
            page_id = await self.notion_sync.create_task(task_rel)
            if page_id:
                await self.task_repository.update(task, notion_page_id=page_id)
                await self.task_repository.commit()
        except Exception as exc:
            logger.error(f"Notion create sync failed (task {task.id}): {exc}")

    async def _notion_update(self, task: Task) -> None:
        """After update-commit: mirror DB state to Notion."""
        if not self.notion_sync:
            return
        try:
            task_rel = await self.task_repository.get_by_id_with_relations(task.id)
            if task_rel is None:
                return
            await self.notion_sync.update_task(task_rel)
        except Exception as exc:
            logger.error(f"Notion update sync failed (task {task.id}): {exc}")

    async def _notion_archive(self, task: Task) -> None:
        """After cancel-commit: archive the Notion page."""
        if not self.notion_sync:
            return
        try:
            await self.notion_sync.archive_task(task)
        except Exception as exc:
            logger.error(f"Notion archive sync failed (task {task.id}): {exc}")

    # ── Task CRUD ──────────────────────────────────────────────────────────

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
        """Create a new task. DB commit first, Notion sync after."""
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
        await self._notion_create(task)
        return task

    async def get_task(self, task_id: int) -> Task:
        """Get task by ID."""
        task = await self.task_repository.get_by_id(task_id)
        if not task:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def get_task_with_relations(self, task_id: int) -> Task:
        """Get task by ID with applicant and executor eagerly loaded."""
        task = await self.task_repository.get_by_id_with_relations(task_id)
        if not task:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def get_task_by_notion_id(self, notion_page_id: str) -> Task | None:
        """Get task by Notion page ID."""
        return await self.task_repository.get_by_notion_id(notion_page_id)

    async def get_user_tasks(self, user_id: int) -> list[Task]:
        """Get all tasks for a user (as applicant)."""
        return await self.task_repository.get_by_applicant(user_id)

    async def get_all_tasks(self) -> list[Task]:
        """Get all tasks (admin use)."""
        return await self.task_repository.get_all()

    async def get_new_tasks(self) -> list[Task]:
        """Get all NEW tasks."""
        return await self.task_repository.get_new_tasks()

    async def get_new_tasks_for_executor_type(self, task_type: TaskType) -> list[Task]:
        """Get NEW tasks filtered by task type for a specific executor specialisation."""
        return await self.task_repository.get_new_tasks_for_executor_type(task_type)

    async def get_executor_tasks(self, executor_id: int) -> list[Task]:
        """Get IN_PROGRESS and WAITING_EXECUTOR tasks for executor."""
        return await self.task_repository.get_executor_in_progress_tasks(executor_id)

    async def get_user_waiting_tasks(self, user_id: int) -> list[Task]:
        """Get WAITING_APPLICANT tasks for user (as applicant)."""
        return await self.task_repository.get_waiting_for_applicant(user_id)

    async def take_task(self, task_id: int, executor_id: int) -> Task:
        """Take task into progress."""
        task = await self.get_task(task_id)
        if task.status != TaskStatus.NEW:
            raise ValueError(f"Task {task_id} is not in NEW status")
        task = await self.task_repository.update(
            task, executor_id=executor_id, status=TaskStatus.IN_PROGRESS,
        )
        await self.task_repository.commit()
        await self._notion_update(task)
        return task

    async def complete_task(self, task_id: int, feedback: str) -> Task:
        """Complete task and request applicant confirmation."""
        task = await self.get_task(task_id)
        if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.WAITING_EXECUTOR]:
            raise ValueError(f"Task {task_id} cannot be completed in {task.status} status")
        task = await self.task_repository.update(
            task, status=TaskStatus.WAITING_APPLICANT, feedback=feedback,
        )
        await self.task_repository.commit()
        await self._notion_update(task)
        return task

    async def confirm_task(self, task_id: int) -> Task:
        """Confirm task completion by applicant."""
        task = await self.get_task(task_id)
        if task.status != TaskStatus.WAITING_APPLICANT:
            raise ValueError(f"Task {task_id} is not waiting for applicant confirmation")
        task = await self.task_repository.update(
            task, status=TaskStatus.DONE, closed_at=datetime.utcnow(),
        )
        await self.task_repository.commit()
        await self._notion_update(task)
        return task

    async def reject_task(self, task_id: int) -> Task:
        """Reject task completion: return to IN_PROGRESS and clear feedback."""
        task = await self.get_task(task_id)
        if task.status != TaskStatus.WAITING_APPLICANT:
            raise ValueError(f"Task {task_id} is not waiting for applicant confirmation")
        task = await self.task_repository.update(
            task, status=TaskStatus.IN_PROGRESS, feedback=None,
        )
        await self.task_repository.commit()
        await self._notion_update(task)
        return task

    async def cancel_task(self, task_id: int) -> Task:
        """Cancel task and archive Notion page."""
        task = await self.get_task(task_id)
        task = await self.task_repository.update(
            task, status=TaskStatus.CANCELLED, closed_at=datetime.utcnow(),
        )
        await self.task_repository.commit()
        await self._notion_archive(task)
        return task

    async def patch_task(
        self,
        task_id: int,
        status: TaskStatus | None = None,
        feedback: str | None = None,
        executor_id: int | None = None,
    ) -> Task:
        """General-purpose administrative task update. Applies only the provided fields."""
        task = await self.get_task(task_id)
        update_kwargs: dict = {}
        if status is not None:
            update_kwargs["status"] = status
        if feedback is not None:
            update_kwargs["feedback"] = feedback
        if executor_id is not None:
            update_kwargs["executor_id"] = executor_id
        if update_kwargs:
            task = await self.task_repository.update(task, **update_kwargs)
            await self.task_repository.commit()
            await self._notion_update(task)
        return task

    async def update_notion_page_id(self, task_id: int, notion_page_id: str) -> Task:
        """Update Notion page ID for a task."""
        task = await self.get_task(task_id)
        task = await self.task_repository.update(task, notion_page_id=notion_page_id)
        await self.task_repository.commit()
        return task

    async def update_task_status(self, task_id: int, status: TaskStatus) -> Task:
        """Update task status."""
        task = await self.get_task(task_id)
        task = await self.task_repository.update(task, status=status)
        await self.task_repository.commit()
        await self._notion_update(task)
        return task

    async def sync_all_to_notion(self) -> dict:
        """Bulk-sync all DB tasks to Notion. Persists new notion_page_ids.

        Returns a summary dict: {created, updated, orphaned, errors}.
        """
        if not self.notion_sync:
            logger.warning("sync_all_to_notion: no NotionSyncService injected")
            return {"created": 0, "updated": 0, "orphaned": 0, "errors": 0}

        tasks = await self.task_repository.get_all_with_relations()
        summary = await self.notion_sync.sync_all_tasks(tasks)

        # Persist any newly assigned notion_page_ids back to DB
        for task in tasks:
            if task.notion_page_id:
                db_task = await self.task_repository.get_by_id(task.id)
                if db_task and db_task.notion_page_id != task.notion_page_id:
                    await self.task_repository.update(db_task, notion_page_id=task.notion_page_id)

        await self.task_repository.commit()
        return summary


# Avoid circular import — imported only for type hints
from app.services.notion_sync_service import NotionSyncService  # noqa: E402, F401
