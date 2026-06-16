"""AI Service for ticket classification."""

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

    async def classify_ticket(self, description: str) -> AIClassificationResponse:
        """Classify a ticket using AI."""
        import httpx
        import json

        if not self.api_key:
            raise AIServiceError("OpenRouter API key not configured")

        prompt = self._build_prompt(description)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "helpdesk-telegram-bot",
                        "X-Title": "HelpDesk Bot",
                    },
                    json={
                        "model": "openai/gpt-3.5-turbo",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a helpdesk ticket classifier. Respond only with valid JSON.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]
                # Extract JSON from response
                classification_data = json.loads(content)

                return AIClassificationResponse(
                    title=classification_data.get("title", ""),
                    description=classification_data.get("description", ""),
                    type=TaskType[classification_data.get("type", "SYSTEM").upper()],
                    priority=TaskPriority[
                        classification_data.get("priority", "MEDIUM").upper()
                    ],
                    executor=classification_data.get("executor", "SysAdmin"),
                )

        except Exception as e:
            raise AIServiceError(f"Failed to classify ticket: {str(e)}")

    def _build_prompt(self, description: str) -> str:
        """Build prompt for AI classification."""
        return f"""Classify the following helpdesk ticket and respond with JSON:

Ticket Description: {description}

Classify the ticket by providing a JSON response with the following structure:
{{
    "title": "Brief title of the issue",
    "description": "Detailed description of the issue",
    "type": "SYSTEM or LOCAL",
    "priority": "LOW, MEDIUM, or HIGH",
    "executor": "SysAdmin or Caretaker"
}}

Rules:
- SYSTEM: Issues related to computers, printers, network, internet, software, servers, IT equipment. Assign to: SysAdmin
- LOCAL: Issues related to furniture, doors, lighting, facility maintenance, office infrastructure. Assign to: Caretaker
- Priority: Determine based on urgency and impact
- Executor: Either SysAdmin or Caretaker based on type

Respond ONLY with the JSON object, no additional text."""
