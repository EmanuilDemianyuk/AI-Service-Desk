"""Notion service for Notion integration."""

from app.config import settings
from app.database.models import Task, TaskStatus, TaskType, TaskPriority
from app.exceptions import NotionServiceError


class NotionService:
    """Service for Notion operations."""

    def __init__(self) -> None:
        self.token = settings.NOTION_TOKEN
        self.database_id = settings.NOTION_DATABASE_ID

    async def create_task_page(self, task: Task) -> str | None:
        """Create a task page in Notion."""
        if not self.token or not self.database_id:
            return None

        try:
            from notion_client import AsyncClient

            client = AsyncClient(auth=self.token)

            response = await client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "Task ID": {"title": [{"text": {"content": str(task.id)}}]},
                    "Title": {"rich_text": [{"text": {"content": task.title}}]},
                    "Description": {"rich_text": [{"text": {"content": task.description or ""}}]},
                    "Type": {
                        "select": {
                            "name": task.type.value if isinstance(task.type, TaskType) else task.type
                        }
                    },
                    "Priority": {
                        "select": {
                            "name": task.priority.value
                            if isinstance(task.priority, TaskPriority)
                            else task.priority
                        }
                    },
                    "Status": {
                        "select": {
                            "name": task.status.value
                            if isinstance(task.status, TaskStatus)
                            else task.status
                        }
                    },
                    "Applicant": {"rich_text": [{"text": {"content": task.applicant.full_name}}]},
                    "Executor": {
                        "rich_text": [
                            {"text": {"content": task.executor.full_name if task.executor else ""}}
                        ]
                    },
                    "Created At": {"date": {"start": task.created_at.isoformat()}},
                },
            )

            return response["id"]

        except Exception as e:
            raise NotionServiceError(f"Failed to create Notion page: {str(e)}")

    async def update_task_page(self, task: Task) -> None:
        """Update a task page in Notion."""
        if not self.token or not task.notion_page_id:
            return

        try:
            from notion_client import AsyncClient

            client = AsyncClient(auth=self.token)

            update_data: dict = {
                "Status": {
                    "select": {
                        "name": task.status.value
                        if isinstance(task.status, TaskStatus)
                        else task.status
                    }
                },
            }

            if task.feedback:
                update_data["Feedback"] = {"rich_text": [{"text": {"content": task.feedback}}]}

            if task.closed_at:
                update_data["Closed At"] = {"date": {"start": task.closed_at.isoformat()}}

            if task.executor:
                update_data["Executor"] = {
                    "rich_text": [{"text": {"content": task.executor.full_name}}]
                }

            await client.pages.update(
                page_id=task.notion_page_id,
                properties=update_data,
            )

        except Exception as e:
            raise NotionServiceError(f"Failed to update Notion page: {str(e)}")

    async def get_task_page(self, notion_page_id: str) -> dict:
        """Get a task page from Notion."""
        if not self.token:
            return {}

        try:
            from notion_client import AsyncClient

            client = AsyncClient(auth=self.token)
            response = await client.pages.retrieve(notion_page_id)
            return response

        except Exception as e:
            raise NotionServiceError(f"Failed to retrieve Notion page: {str(e)}")
