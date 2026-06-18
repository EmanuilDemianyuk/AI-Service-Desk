"""AI Service for ticket classification."""

import json

from pydantic import BaseModel, Field

from app.config import settings
from app.database.models import TaskType, TaskPriority
from app.exceptions import AIServiceError


class AIClassificationResponse(BaseModel):
    """AI classification response."""

    title: str = Field(..., description="Task title (Ukrainian)")
    description: str = Field(..., description="Task description (Ukrainian)")
    type: TaskType = Field(..., description="Task type (SYSTEM or LOCAL)")
    priority: TaskPriority = Field(..., description="Task priority")


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
                                    "Ти — класифікатор заявок служби підтримки. "
                                    "Завжди відповідай виключно українською мовою. "
                                    "Відповідай тільки валідним JSON."
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

                task_type = classification_data.get("type", "SYSTEM").upper()
                priority = classification_data.get("priority", "MEDIUM").upper()

                return AIClassificationResponse(
                    title=classification_data.get("title", "Без назви"),
                    description=classification_data.get("description", description),
                    type=TaskType[task_type],
                    priority=TaskPriority[priority],
                )

        except httpx.HTTPStatusError as e:
            raise AIServiceError(
                f"OpenRouter API error: "
                f"{e.response.status_code} - {e.response.text}"
            ) from e

        except AIServiceError:
            raise

        except Exception as e:
            raise AIServiceError(
                f"Failed to classify ticket: {str(e)}"
            ) from e

    def _build_prompt(self, description: str) -> str:
        """Build prompt for AI classification."""

        return f"""Класифікуй наступну заявку служби підтримки та поверни JSON.

Опис заявки:
{description}

Поверни ТІЛЬКИ JSON-об'єкт такої структури:

{{
    "title": "Коротка назва проблеми українською мовою",
    "description": "Детальний опис проблеми українською мовою",
    "type": "SYSTEM або LOCAL",
    "priority": "LOW, MEDIUM або HIGH"
}}

Правила визначення типу:

- SYSTEM:
  Комп'ютери, принтери, інтернет, Wi-Fi, мережа,
  програмне забезпечення, сервери, електронна пошта, IT-обладнання.

- LOCAL:
  Меблі, двері, вікна, освітлення,
  сантехніка, офісна інфраструктура,
  господарські питання.

Правила визначення пріоритету:

- HIGH: Робота зупинена, критична система недоступна, постраждало багато користувачів.
- MEDIUM: Робота ускладнена, але можлива.
- LOW: Незначні незручності.

Важливо:
- Повертай ТІЛЬКИ категорії SYSTEM або LOCAL — інші категорії неприпустимі.
- Текст полів title та description — виключно українською мовою.
- НЕ визначай виконавця — це виконує серверна логіка.
- Відповідай ТІЛЬКИ валідним JSON.
"""
