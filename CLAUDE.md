# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HelpDesk AI Telegram Bot — an automated helpdesk ticket management system. Employees submit requests through Telegram; AI classifies them and routes to the correct executor (SysAdmin for IT issues, Caretaker for facilities). Tasks are persisted in PostgreSQL and optionally synced to Notion.

Two processes run separately:
- **FastAPI server** (`app/main.py`) — REST API + database initialization
- **Bot runner** (`app/bot_runner.py`) — aiogram polling loop

## Commands

### Local development

```bash
# Setup
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Database
alembic upgrade head

# Run (two terminals)
uvicorn app.main:app --reload
python app/bot_runner.py
```

### Docker (recommended)

```bash
docker-compose up -d
docker-compose logs -f app
docker-compose down
```

### Code quality

```bash
bash format.sh    # black + isort
bash check.sh     # pytest + mypy + flake8 + formatting check
mypy app/
flake8 app/
pytest --cov=app
```

### Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

## Architecture

### Layer structure

```
Telegram Bot / FastAPI   ← Presentation
      ↓
Bot Handlers / Routes    ← Interface Adapters
      ↓
Services                 ← Business Logic (UserService, TaskService, AIService, NotionService)
      ↓
Repositories             ← Data Access (UserRepository, TaskRepository)
      ↓
PostgreSQL / OpenRouter / Notion   ← External
```

### Key architectural decisions

**Dependency injection via `app/services/dependencies.py`**: Services are constructed by combining a repository with a DB session. The bot injects them via `dp.workflow_data`; FastAPI routes use `Depends()`.

**Two-process design**: The FastAPI server and bot runner share the same SQLAlchemy models and services but run as separate processes. `app/main.py` initializes the schema on startup (`Base.metadata.create_all`), so the API server must be healthy before the bot can create tasks.

**Notion is optional**: All Notion calls silently skip (return `None`) when `NOTION_TOKEN` or `NOTION_DATABASE_ID` are absent. Never gate logic on Notion availability.

**AI via OpenRouter**: `app/services/ai_service.py` calls the `qwen/qwen3-32b` model with `response_format: json_object`. It returns an `AIClassificationResponse` with `type` (SYSTEM/LOCAL), `priority` (LOW/MEDIUM/HIGH), and `executor` (SysAdmin/Caretaker).

### Bot FSM states

Three state groups in `app/bot/states/states.py`:
- `ApplicantStates` — main menu, create request, view requests
- `ExecutorStates` — new tasks, in-progress tasks, feedback input
- `AdminStates` — admin menu

User role is stored in the DB (`UserRole.APPLICANT / EXECUTOR / ADMIN`). Handler routers must filter by both state and role; the role is resolved from `UserService.get_user_by_telegram_id`.

### Task lifecycle

```
NEW → IN_PROGRESS → WAITING_APPLICANT → DONE
                  ↘ IN_PROGRESS (rejected) → WAITING_EXECUTOR → WAITING_APPLICANT
NEW → CANCELLED
```

### Enums

All enums live in the model files and are used as `str` enums (e.g., `TaskStatus(str, enum.Enum)`), so they serialize to/from plain strings without extra conversion.

## Configuration

All settings are in `app/config/settings.py` via Pydantic `BaseSettings`. Required:
- `BOT_TOKEN`
- `SUPERADMIN_TELEGRAM_ID`
- `POSTGRES_*` (host, port, db, user, password)

Optional (features degrade gracefully without them):
- `OPENROUTER_API_KEY` — AI classification disabled if absent
- `NOTION_TOKEN` + `NOTION_DATABASE_ID` — Notion sync disabled if absent

The DB URL is a `cached_property`; use `settings.DATABASE_URL` (async/asyncpg) and `settings.DATABASE_URL_SYNC` (sync/psycopg, used by Alembic).

## Code conventions

- All I/O is `async/await` throughout (SQLAlchemy `AsyncSession`, `httpx.AsyncClient`, `notion_client.AsyncClient`)
- Full type hints required on all function signatures (`Mapped[...]` for ORM columns)
- `line-length = 100` (black), `profile = "black"` (isort)
- Custom exceptions extend `AppException` from `app/exceptions/exceptions.py`; use the specific subclass (e.g., `AIServiceError`, `NotionServiceError`)
- Logging via `app/core/logging.py` (`setup_logging()` + `get_logger(__name__)`) — use structured logging, not `print`
