"""AI Service for ticket classification."""

import json

from pydantic import BaseModel, Field

from app.config import settings
from app.database.models import TaskType, TaskPriority
from app.exceptions import AIServiceError


class AIClassificationResponse(BaseModel):
    """AI classification response."""

    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    type: TaskType = Field(..., description="Task type (SYSTEM or LOCAL)")
    priority: TaskPriority = Field(..., description="Task priority")
    executor: str = Field(..., description="Executor name (SysAdmin or Caretaker)")


class AIService:
    """Service for AI operations."""

    def __init__(self) -> None:
        self.api_key = settings.OPENROUTER_API_KEY

    async def classify_ticket(
        self,
        description: str,
    ) -> AIClassificationResponse:
        """Classify a ticket using AI."""

        import httpx

        if not self.api_key:
            raise AIServiceError("OpenRouter API key not configured")

        prompt = self._build_prompt(description)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "https://helpdesk.local",
                        "X-Title": "HelpDesk Bot",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "qwen/qwen3-32b",
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a helpdesk ticket classifier. "
                                    "Respond only with valid JSON."
                                ),
                            },
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        "temperature": 0,
                        "response_format": {
                            "type": "json_object"
                        },
                    },
                )

                response.raise_for_status()

                data = response.json()

                try:
                    content = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as e:
                    raise AIServiceError(
                        f"Unexpected OpenRouter response: {data}"
                    ) from e

                try:
                    classification_data = json.loads(content)
                except json.JSONDecodeError as e:
                    raise AIServiceError(
                        f"Model returned invalid JSON: {content}"
                    ) from e

                task_type = classification_data.get(
                    "type",
                    "SYSTEM",
                ).upper()

                priority = classification_data.get(
                    "priority",
                    "MEDIUM",
                ).upper()

                return AIClassificationResponse(
                    title=classification_data.get(
                        "title",
                        "Untitled ticket",
                    ),
                    description=classification_data.get(
                        "description",
                        description,
                    ),
                    type=TaskType[task_type],
                    priority=TaskPriority[priority],
                    executor=classification_data.get(
                        "executor",
                        "SysAdmin",
                    ),
                )

        except httpx.HTTPStatusError as e:
            raise AIServiceError(
                f"OpenRouter API error: "
                f"{e.response.status_code} - {e.response.text}"
            ) from e

        except Exception as e:
            raise AIServiceError(
                f"Failed to classify ticket: {str(e)}"
            ) from e

    def _build_prompt(self, description: str) -> str:
        """Build prompt for AI classification."""

        return f"""
Classify the following helpdesk ticket and respond with JSON.

Ticket Description:
{description}

Return ONLY a JSON object with this structure:

{{
    "title": "Brief title of the issue",
    "description": "Detailed description of the issue",
    "type": "SYSTEM or LOCAL",
    "priority": "LOW, MEDIUM, or HIGH",
    "executor": "SysAdmin or Caretaker"
}}

Rules:

- SYSTEM:
  Computers, printers, internet, Wi-Fi, network,
  software, servers, email, IT equipment.
  Executor: SysAdmin

- LOCAL:
  Furniture, doors, windows, lighting,
  plumbing, office infrastructure,
  maintenance issues.
  Executor: Caretaker

- HIGH:
  Work stopped, critical system unavailable,
  many users affected.

- MEDIUM:
  Work degraded but possible.

- LOW:
  Minor inconvenience.

Respond ONLY with valid JSON.
"""

