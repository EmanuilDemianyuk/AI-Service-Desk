"""Centralised Notion synchronisation service.

Single source of truth: application database.
Notion is an external display layer — all writes go to DB first,
then are mirrored here. Notion errors never rollback DB transactions.
"""

from __future__ import annotations

from app.config import settings
from app.core.logging import get_logger
from app.database.models import Task

logger = get_logger(__name__)


def _safe_str(value: object) -> str:
    return str(value) if value is not None else ""


def _build_full_properties(task: Task) -> dict:
    """Build full Notion property payload from a task (relations must be loaded)."""
    applicant_name = (
        task.applicant.full_name if task.applicant else _safe_str(task.applicant_id)
    )
    executor_name = task.executor.full_name if task.executor else ""

    return {
        "Task ID":     {"title": [{"text": {"content": str(task.id)}}]},
        "Title":       {"rich_text": [{"text": {"content": task.title}}]},
        "Description": {"rich_text": [{"text": {"content": task.description or ""}}]},
        "Type":        {"select": {"name": task.type.value}},
        "Priority":    {"select": {"name": task.priority.value}},
        "Status":      {"select": {"name": task.status.value}},
        "Applicant":   {"rich_text": [{"text": {"content": applicant_name}}]},
        "Executor":    {"rich_text": [{"text": {"content": executor_name}}]},
        "Created At":  {"date": {"start": task.created_at.isoformat()}},
        "Feedback":    {"rich_text": [{"text": {"content": task.feedback or ""}}]},
    }


class NotionSyncService:
    """Handles all Notion API interactions for task synchronisation."""

    def __init__(self) -> None:
        self._token = settings.NOTION_TOKEN
        self._database_id = settings.NOTION_DATABASE_ID

    @property
    def enabled(self) -> bool:
        return bool(self._token and self._database_id)

    def _client(self):  # type: ignore[return]
        from notion_client import AsyncClient
        return AsyncClient(auth=self._token)

    # ── Public interface ───────────────────────────────────────────────────

    async def create_task(self, task: Task) -> str | None:
        """Create a Notion page for a task. Returns the new page_id or None."""
        if not self.enabled:
            return None
        try:
            client = self._client()
            response = await client.pages.create(
                parent={"database_id": self._database_id},
                properties=_build_full_properties(task),
            )
            page_id: str = response["id"]
            logger.info(f"Notion page created for task {task.id}: {page_id}")
            return page_id
        except Exception as exc:
            logger.error(f"Notion create_task failed for task {task.id}: {exc}")
            return None

    async def update_task(self, task: Task) -> None:
        """Update an existing Notion page to mirror DB state."""
        if not self.enabled or not task.notion_page_id:
            return
        try:
            client = self._client()
            await client.pages.update(
                page_id=task.notion_page_id,
                properties=_build_full_properties(task),
            )
            logger.info(f"Notion page updated for task {task.id}")
        except Exception as exc:
            logger.error(f"Notion update_task failed for task {task.id}: {exc}")

    async def archive_task(self, task: Task) -> None:
        """Archive the Notion page (soft-delete). DB record is unchanged."""
        if not self.enabled or not task.notion_page_id:
            return
        try:
            client = self._client()
            await client.pages.update(
                page_id=task.notion_page_id,
                archived=True,
            )
            logger.info(f"Notion page archived for task {task.id}")
        except Exception as exc:
            logger.error(f"Notion archive_task failed for task {task.id}: {exc}")

    async def sync_task(self, task: Task) -> str | None:
        """Create or update Notion page based on whether notion_page_id exists.

        Returns the page_id (new or existing) so the caller can persist it.
        """
        if not self.enabled:
            return None
        if task.notion_page_id:
            await self.update_task(task)
            return task.notion_page_id
        else:
            return await self.create_task(task)

    async def sync_all_tasks(self, tasks: list[Task]) -> dict:
        """Bulk-sync all DB tasks to Notion. DB is authoritative.

        Returns a summary: {created, updated, orphaned, errors}.
        """
        if not self.enabled:
            logger.warning("Notion sync disabled — token or database_id not set")
            return {"created": 0, "updated": 0, "orphaned": 0, "errors": 0}

        summary = {"created": 0, "updated": 0, "orphaned": 0, "errors": 0}

        # Collect all known Notion page IDs from DB
        db_page_ids: set[str] = {t.notion_page_id for t in tasks if t.notion_page_id}

        # Fetch all pages currently in Notion (paginate)
        notion_page_ids: set[str] = set()
        try:
            client = self._client()
            cursor = None
            while True:
                kwargs: dict = {"database_id": self._database_id, "page_size": 100}
                if cursor:
                    kwargs["start_cursor"] = cursor
                result = await client.databases.query(**kwargs)
                for page in result["results"]:
                    notion_page_ids.add(page["id"])
                if not result.get("has_more"):
                    break
                cursor = result.get("next_cursor")
        except Exception as exc:
            logger.error(f"Notion sync_all: failed to fetch existing pages: {exc}")
            summary["errors"] += 1

        # Sync each DB task → Notion
        for task in tasks:
            try:
                if task.notion_page_id and task.notion_page_id in notion_page_ids:
                    await self.update_task(task)
                    summary["updated"] += 1
                else:
                    page_id = await self.create_task(task)
                    if page_id:
                        # Caller must persist this — we return per-task IDs via yielded results
                        # For bulk sync we store it back via the task object attribute
                        task.notion_page_id = page_id  # in-memory; caller commits
                        summary["created"] += 1
                    else:
                        summary["errors"] += 1
            except Exception as exc:
                logger.error(f"Notion sync_all: error for task {task.id}: {exc}")
                summary["errors"] += 1

        # Log orphaned Notion pages (exist in Notion but not in any DB task)
        orphaned = notion_page_ids - db_page_ids
        for orphan_id in orphaned:
            logger.warning(f"Notion orphan (not in DB): page_id={orphan_id}")
        summary["orphaned"] = len(orphaned)

        logger.info(f"Notion sync_all complete: {summary}")
        return summary
