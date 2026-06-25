# Architecture Overview

This document describes the architecture and design patterns used in the HelpDesk Bot application.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Users                        │
│            (Applicant / Executor / Admin)                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ (aiogram 3.x — polling)
                       ▼
┌─────────────────────────────────────────────────────────┐
│         Telegram Bot                                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Middleware Layer                                 │   │
│  │  ├─ CommandGuardMiddleware                        │   │
│  │  └─ NavDeleteMiddleware                           │   │
│  ├──────────────────────────────────────────────────┤   │
│  │  Handlers Layer (FSM-based)                       │   │
│  │  ├─ Common Handlers (/start, /help, /cancel)      │   │
│  │  ├─ Applicant Handlers                            │   │
│  │  ├─ Executor Handlers                             │   │
│  │  └─ Admin Handlers                                │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────────┐ ┌──────────────┐
│ UserService  │ │   TaskService    │ │  AIService   │
│              │ │  + Notion        │ │              │
│              │ │  SyncService     │ │              │
└──────────────┘ └──────────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│         Repositories (Data Access Layer)                 │
│  ┌──────────────────────────────────────────────────┐   │
│  │  UserRepository      │  TaskRepository            │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ OpenRouter   │ │    Notion    │
│   Database   │ │   (AI API)   │ │   (mirror)   │
└──────────────┘ └──────────────┘ └──────────────┘

┌──────────────────────────────────────────────────────────┐
│         FastAPI REST API                                 │
│  ├─ GET  /health                                         │
│  ├─ POST /api/users                                      │
│  ├─ GET  /api/users                                      │
│  ├─ PATCH /api/users/{user_id}                           │
│  ├─ GET  /api/tasks                                      │
│  ├─ GET  /api/tasks/{task_id}                            │
│  ├─ POST /api/tasks                                      │
│  ├─ PATCH /api/tasks/{task_id}/status                    │
│  └─ POST /api/notion/sync                                │
└──────────────────────────────────────────────────────────┘
```

---

## Design Patterns

### 1. Repository Pattern

**Purpose**: Abstract database access and provide a uniform interface.

```python
# app/database/repositories/user_repository.py
class UserRepository(BaseRepository):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        ...
```

**Benefits**: Decouples business logic from database, centralizes query logic.

---

### 2. Service Layer Pattern

**Purpose**: Encapsulate business logic separate from presentation and data layers.

```python
# app/services/user_service.py
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def get_or_create_user(self, telegram_id: int, ...) -> User:
        ...
```

**Benefits**: Reusable business logic across bot handlers and API routes.

---

### 3. Dependency Injection

**Purpose**: Manage service dependencies and enable loose coupling.

- **Bot**: Services are injected via `dp.workflow_data` in `bot_runner.py` and accessed directly in handlers.
- **FastAPI**: Routes use `Depends(get_db_session)` and construct services inline; `app/services/dependencies.py` provides factory functions.

---

### 4. Finite State Machine (FSM)

**Purpose**: Manage bot conversation flow and state transitions.

Three state groups defined in `app/bot/states/states.py`:

```python
class ApplicantStates(StatesGroup):
    main_menu = State()
    create_request = State()
    request_description = State()    # active flow — user is typing
    my_requests = State()
    request_status = State()
    status_input = State()           # active flow
    confirm_requests = State()
    confirm_request_detail = State()
    my_request_detail = State()

class ExecutorStates(StatesGroup):
    main_menu = State()
    new_tasks = State()
    new_task_detail = State()
    my_tasks = State()
    task_in_progress = State()
    complete_task = State()          # active flow
    feedback_input = State()         # active flow — user is typing
    task_confirmation = State()

class AdminStates(StatesGroup):
    main_menu = State()
    user_list = State()
    user_detail = State()
    set_role_select_role = State()
    set_role_executor_type = State()
    confirm_delete_user = State()
    create_user_first_name = State()  # active flow
    create_user_last_name = State()   # active flow
    create_user_telegram_id = State() # active flow
    create_user_role = State()        # active flow
    create_user_executor_type = State() # active flow
    task_list = State()
```

`FLOW_STATES` is a `frozenset` of states where the user is actively entering data — used by middleware to protect in-progress input.

---

### 5. Middleware Layer

Two middleware classes run on every incoming message.

#### CommandGuardMiddleware (`app/bot/middleware/command_guard.py`)

Intercepts slash commands (`/start`, `/help`, etc.) while a user is inside an active multi-step flow (state is in `FLOW_STATES`). Shows an inline confirmation prompt instead of aborting the flow silently.

- `/cancel` bypasses the guard unconditionally.
- Saves the pending command to FSM data; `guard_confirm` / `guard_cancel` callbacks in `common.py` handle the response.

#### NavDeleteMiddleware (`app/bot/middleware/nav_delete.py`)

Silently deletes ReplyKeyboard navigation button messages (e.g., «🏠 Головне меню», «⬅️ Назад») to keep the chat uncluttered. Messages in `FLOW_STATES` (user input) are never deleted.

---

### 6. Clean Architecture

**Layers** (innermost to outermost):

1. **Entities** — Domain models (`User`, `Task`, enums)
2. **Use Cases** — Business logic (Services)
3. **Interface Adapters** — Repositories, API routes, Bot handlers
4. **External Interfaces** — Database, APIs, Telegram

---

## Data Flow

### Task Creation Flow

```
User sends problem description (ApplicantStates.request_description)
    ↓
UserService.get_user_by_telegram_id()  — resolve DB user
    ↓
AIService.classify_ticket(description)
    ↓
OpenRouter API (qwen/qwen3-32b) — returns JSON
    {title, description, type (SYSTEM|LOCAL), priority (LOW|MEDIUM|HIGH)}
    ↓
UserService.get_executor_for_type(task_type)
    SYSTEM → ExecutorType.SYSADMIN
    LOCAL  → ExecutorType.MASTER
    Raises NoExecutorError if no executor of required type exists
    ↓
TaskService.create_task(...)
    ↓
TaskRepository.create() + commit()    — DB is source of truth
    ↓
NotionSyncService.create_task()       — non-blocking, errors logged only
    ↓
Response sent to applicant
```

> **Important**: The AI model does **not** determine the executor. Executor assignment is
> server-side business logic based on `task_type` → `ExecutorType` mapping.

### Notion Sync Strategy

`TaskService` manages Notion as a read-only mirror of the database:

- Every successful DB commit is followed by a fire-and-forget Notion sync.
- Notion errors are logged but **never** propagated — they do not roll back DB transactions.
- All Notion sync is handled by `NotionSyncService` (`app/services/notion_sync_service.py`).
- `NotionService` (`app/services/notion_service.py`) is a legacy direct-CRUD client kept for backward compatibility.

| DB operation | Notion operation |
|---|---|
| `create_task` | `create_task` (persists `page_id` back to DB) |
| `take_task`, `complete_task`, `confirm_task`, `reject_task` | `update_task` |
| `cancel_task` | `archive_task` |
| `POST /api/notion/sync` | `sync_all_tasks` (bulk reconciliation) |

---

## Database Schema

### ERD

```
Users Table
┌──────────────────────────────────┐
│ id (PK)                          │
│ telegram_id (UNIQUE, NOT NULL)   │
│ full_name (NOT NULL)             │
│ username                         │
│ role (APPLICANT│EXECUTOR│ADMIN)  │
│ type (SYSADMIN│MASTER│NULL)      │  ← only set for EXECUTOR role
│ is_active                        │
│ created_at                       │
└──────────────────────────────────┘
          ▲         ▲
    (1:N) │         │ (1:N)
          │ FK      │ FK
          │         │
Tasks Table
┌──────────────────────────────────┐
│ id (PK)                          │
│ notion_page_id                   │
│ applicant_id (FK → users.id)     │
│ executor_id  (FK → users.id)     │
│ title (NOT NULL)                 │
│ description                      │
│ type (SYSTEM│LOCAL)              │
│ priority (LOW│MEDIUM│HIGH)       │
│ status                           │
│ feedback                         │
│ created_at                       │
│ closed_at                        │
└──────────────────────────────────┘
```

### Enums

| Enum | Values |
|---|---|
| `UserRole` | `APPLICANT`, `EXECUTOR`, `ADMIN` |
| `ExecutorType` | `SYSADMIN`, `MASTER` — only valid for `EXECUTOR` role |
| `TaskType` | `SYSTEM`, `LOCAL` |
| `TaskPriority` | `LOW`, `MEDIUM`, `HIGH` |
| `TaskStatus` | `NEW`, `IN_PROGRESS`, `WAITING_APPLICANT`, `WAITING_EXECUTOR`, `DONE`, `CANCELLED` |

All enums extend both `str` and `enum.Enum` so they serialize to plain strings without conversion.

### Task Lifecycle

```
NEW
├─> IN_PROGRESS           (executor takes task via «🆕 Нові завдання»)
│   └─> WAITING_APPLICANT (executor marks complete with feedback)
│       ├─> DONE          (applicant confirms)
│       └─> IN_PROGRESS   (applicant rejects — feedback cleared)
└─> CANCELLED             (task cancelled, Notion page archived)
```

`WAITING_EXECUTOR` is defined in the schema and appears in the executor's active task list query (alongside `IN_PROGRESS`).

---

## Service Responsibilities

### UserService (`app/services/user_service.py`)

- User creation, retrieval, update, deletion
- Auto-assign `ADMIN` role to the user whose `telegram_id` matches `SUPERADMIN_TELEGRAM_ID`
- `get_or_create_user` — upsert on first `/start`
- `get_executor_for_type(task_type)` — strict executor selection by specialization; raises `NoExecutorError` if none available
- `update_user_fields` — partial update with role/type consistency validation
- `delete_user` — deletes user and cascades to their created tasks; clears `executor_id` on assigned tasks

### TaskService (`app/services/task_service.py`)

- Full task CRUD and status transitions
- DB is the single source of truth
- Non-blocking Notion sync via `NotionSyncService` after every commit (errors logged, not raised)
- `sync_all_to_notion()` — bulk reconciliation, persists new `notion_page_id`s back to DB

### AIService (`app/services/ai_service.py`)

- Calls OpenRouter (`qwen/qwen3-32b`) with `response_format: json_object`
- Returns `AIClassificationResponse`: `{title, description, type, priority}` — all text in Ukrainian
- Does **not** determine the executor; executor selection is a server-side responsibility

### NotionSyncService (`app/services/notion_sync_service.py`)

- Central Notion integration used by `TaskService`
- Gracefully no-ops when `NOTION_TOKEN` or `NOTION_DATABASE_ID` are absent (`enabled` property)
- Methods: `create_task`, `update_task`, `archive_task`, `sync_task`, `sync_all_tasks`
- `sync_all_tasks` paginates Notion, detects orphan pages, returns a `{created, updated, orphaned, errors}` summary

### NotionService (`app/services/notion_service.py`)

- Legacy direct-CRUD Notion client; kept for backward compatibility
- Use `NotionSyncService` for all new code

---

## API Routes

### Health

```
GET /health
Response: {"status": "healthy", "message": "Service is running"}
```

### Users

```
POST   /api/users              — create user; EXECUTOR requires type=SYSADMIN|MASTER
GET    /api/users              — list all users
PATCH  /api/users/{user_id}   — partial update; changing from EXECUTOR clears type automatically
```

### Tasks

```
GET    /api/tasks              — list all tasks; Response: {items: [...], total: N}
GET    /api/tasks/{task_id}    — get single task
POST   /api/tasks              — create task
PATCH  /api/tasks/{task_id}/status  — update status, feedback, executor_id
```

### Notion

```
POST   /api/notion/sync        — bulk-sync all DB tasks to Notion
                                 Response: {created, updated, orphaned, errors}
```

---

## Error Handling

### Exception Hierarchy

```
Exception
└─ AppException (base — carries .message and .code)
   ├─ ValidationError
   ├─ NotFoundError
   ├─ AuthenticationError
   ├─ AuthorizationError
   ├─ AIServiceError
   ├─ NotionServiceError
   ├─ TelegramServiceError
   ├─ DatabaseError
   └─ NoExecutorError        — no executor of required type is registered
```

FastAPI maps `AppException` → HTTP 400; `NotFoundError` → HTTP 404; `RequestValidationError` → HTTP 422.

---

## Logging

Logging is configured via `app/core/logging.py` (`setup_logging()` + `get_logger(__name__)`).

- Use structured logging (`get_logger`, not `print`).
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
- Console output for development; file handlers (`logs/app.log`, `logs/error.log`) for all environments.

---

## Security Considerations

1. Sensitive configuration in `.env` only — never hardcoded.
2. Pydantic validation on all API inputs.
3. Bot admin operations guarded by `_assert_admin()` — checks caller's role before every operation.
4. Generic error messages surfaced to Telegram users; full detail only in server logs.

---

## Performance Considerations

1. All I/O is `async/await` throughout (SQLAlchemy `AsyncSession`, `httpx.AsyncClient`, `notion_client.AsyncClient`).
2. SQLAlchemy connection pooling via `create_async_engine`.
3. Notion sync is fire-and-forget — never blocks the bot response.
4. FSM state stored in memory (`MemoryStorage`) — use Redis for multi-instance or restartable deployments.
