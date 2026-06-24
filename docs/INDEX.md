# Project File Index

## Documentation (`docs/`)

| File | Purpose |
|---|---|
| [SETUP.md](SETUP.md) | Installation, configuration, bot usage |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, patterns, data flow, API reference |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment options |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow and code standards |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [INDEX.md](INDEX.md) | This file |

---

## Application (`app/`)

### Entry Points

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI application — initializes DB schema on startup |
| `app/bot_runner.py` | Bot polling loop — injects services via `dp.workflow_data` |

### Configuration (`app/config/`)

| File | Purpose |
|---|---|
| `app/config/settings.py` | Pydantic `BaseSettings` — all env vars with defaults |

### Core Utilities (`app/core/`)

| File | Purpose |
|---|---|
| `app/core/logging.py` | `setup_logging()` and `get_logger()` |

### Database Layer (`app/database/`)

| File | Purpose |
|---|---|
| `app/database/base.py` | SQLAlchemy `create_async_engine`, `AsyncSessionLocal`, `Base` |
| `app/database/session.py` | `get_db_session` FastAPI dependency |
| `app/database/models/user.py` | `User` ORM model, `UserRole` enum, `ExecutorType` enum |
| `app/database/models/task.py` | `Task` ORM model, `TaskStatus`, `TaskType`, `TaskPriority` enums |
| `app/database/repositories/base.py` | Abstract `BaseRepository` |
| `app/database/repositories/user_repository.py` | User data access |
| `app/database/repositories/task_repository.py` | Task data access |

### Services Layer (`app/services/`)

| File | Purpose |
|---|---|
| `app/services/user_service.py` | User CRUD, role management, executor selection |
| `app/services/task_service.py` | Task lifecycle + Notion sync side effects |
| `app/services/ai_service.py` | OpenRouter ticket classification |
| `app/services/notion_sync_service.py` | Centralised Notion sync (preferred) |
| `app/services/notion_service.py` | Direct Notion CRUD (legacy) |
| `app/services/dependencies.py` | Service factory functions for FastAPI and bot |

### Exceptions (`app/exceptions/`)

| File | Purpose |
|---|---|
| `app/exceptions/exceptions.py` | Custom exception hierarchy (`AppException` and subclasses) |

### Schemas (`app/schemas/`)

| File | Purpose |
|---|---|
| `app/schemas/schemas.py` | Pydantic request/response models for API |

### API Layer (`app/api/`)

| File | Purpose |
|---|---|
| `app/api/routes.py` | FastAPI route handlers (users, tasks, Notion sync, health) |

### Telegram Bot (`app/bot/`)

| File | Purpose |
|---|---|
| `app/bot/bot.py` | Bot and dispatcher setup |
| `app/bot/states/states.py` | FSM state groups + `FLOW_STATES` frozenset |
| `app/bot/middleware/command_guard.py` | Intercepts commands during active flows |
| `app/bot/middleware/nav_delete.py` | Deletes navigation messages from chat |
| `app/bot/handlers/common.py` | `/start`, `/help`, `/cancel`, guard callbacks |
| `app/bot/handlers/applicant.py` | Applicant workflow handlers |
| `app/bot/handlers/executor.py` | Executor workflow handlers |
| `app/bot/handlers/admin.py` | Admin panel handlers |
| `app/bot/keyboards/applicant.py` | Applicant keyboard layouts |
| `app/bot/keyboards/executor.py` | Executor keyboard layouts |
| `app/bot/keyboards/admin.py` | Admin keyboard layouts |
| `app/bot/keyboards/localizer.py` | Ukrainian display text for statuses, priorities, types |

---

## Database Migrations (`migrations/`)

| File | Purpose |
|---|---|
| `migrations/env.py` | Alembic environment configuration |
| `migrations/versions/a6ac8a5bb63b_initial.py` | Initial schema — `users` and `tasks` tables |
| `migrations/versions/b1c3e7f2a894_add_executor_type_to_users.py` | Adds `type` column to `users` |

---

## Scripts (`scripts/`)

| File | Purpose |
|---|---|
| `scripts/migrate_tasks_to_ukrainian.py` | One-off script to localise existing task titles/descriptions to Ukrainian |

---

## Root Configuration

| File | Purpose |
|---|---|
| `requirements.txt` | Production Python dependencies |
| `pyproject.toml` | Project metadata and tool configuration |
| `docker-compose.yml` | Multi-container orchestration |
| `Dockerfile` | Container image definition |
| `.env.example` | Environment variables template |
| `.gitignore` | Git ignore patterns |
| `.dockerignore` | Docker ignore patterns |
| `alembic.ini` | Alembic configuration |
| `format.sh` | Run `black` + `isort` |
| `check.sh` | Run `pytest` + `mypy` + `flake8` + formatting check |

---

## Reading Order

### First time

1. [SETUP.md](SETUP.md) — installation and configuration
2. [ARCHITECTURE.md](ARCHITECTURE.md) — system design overview

### Understanding the code

1. `app/config/settings.py` — available configuration
2. `app/database/models/` — domain entities and enums
3. `app/services/` — business logic
4. `app/bot/states/states.py` — FSM structure
5. `app/bot/handlers/` — user-facing flows
6. `app/api/routes.py` — REST API

### Deploying

1. [DEPLOYMENT.md](DEPLOYMENT.md)
2. `docker-compose.yml`
3. `migrations/versions/` — database schema history
