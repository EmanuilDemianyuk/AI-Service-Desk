# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.5.0] — 2026-06-24

### Added

- **Executor task filtering by specialization**: executors now see only tasks that match their type
  - `SYSADMIN` → `SYSTEM` tasks; `MASTER` → `LOCAL` tasks
  - `TaskService.get_new_tasks_for_executor_type(task_type)` added
  - `TaskRepository.get_new_tasks_for_executor_type(task_type)` added
- **New task review flow for executors**: executor views full task card (title, description, applicant, priority, type, date) and explicitly accepts via inline button "✅ Прийняти" before taking responsibility
  - New state `ExecutorStates.new_task_detail`
  - Callback handler `accept_task_callback` — takes task into progress
- **Ukrainian localization**: all bot messages, keyboard labels, AI prompts, and status/priority/type display text are in Ukrainian
  - `app/bot/keyboards/localizer.py` — `STATUS_EMOJI`, `STATUS_TEXT`, `PRIORITY_TEXT`, `TYPE_TEXT` dictionaries

### Changed

- AI prompt now instructs the model to respond exclusively in Ukrainian
- `AIClassificationResponse` now includes `title` (str) and `description` (str) fields returned by the model in Ukrainian; the model does **not** determine the executor
- Task titles and descriptions in the database are stored in Ukrainian

---

## [0.4.0] — 2026

### Added

- **`NavDeleteMiddleware`** (`app/bot/middleware/nav_delete.py`): silently deletes ReplyKeyboard navigation messages (e.g. «🏠 Головне меню», «⬅️ Назад») from the chat. Messages in `FLOW_STATES` (user is typing) are exempt.
- **`CommandGuardMiddleware`** (`app/bot/middleware/command_guard.py`): intercepts slash commands while a user is inside a multi-step input flow. Shows a confirmation prompt; `/cancel` is exempt.
- **`FLOW_STATES` frozenset** in `app/bot/states/states.py`: defines which FSM states represent active user input; used by both middleware classes.

### Changed

- `NotionSyncService` injected into `TaskService` constructor; all Notion sync side-effects are managed within `TaskService` (post-commit, non-blocking).
- `bot_runner.py` now imports and instantiates `NotionSyncService`.

---

## [0.3.0] — 2026

### Added

- **`NotionSyncService`** (`app/services/notion_sync_service.py`): centralized Notion sync service
  - `create_task(task)` — creates a Notion page, returns `page_id`
  - `update_task(task)` — mirrors full task state to Notion
  - `archive_task(task)` — soft-deletes the Notion page on task cancellation
  - `sync_task(task)` — create-or-update based on `notion_page_id`
  - `sync_all_tasks(tasks)` — bulk reconciliation with pagination and orphan detection; returns `{created, updated, orphaned, errors}`
  - Gracefully no-ops when `NOTION_TOKEN` or `NOTION_DATABASE_ID` are absent
- **Notion sync API endpoint**: `POST /api/notion/sync` — triggers `TaskService.sync_all_to_notion()`
- **`TaskService` Notion integration**:
  - `_notion_create`, `_notion_update`, `_notion_archive` — private helpers called after each DB commit
  - `sync_all_to_notion()` — bulk sync, persists new `notion_page_id`s back to DB
- **`get_task_with_relations`** on `TaskService` and repository — eagerly loads `applicant` and `executor` relationships
- **`get_new_tasks`** and **`get_new_tasks_for_executor_type`** on `TaskService`
- **`get_all_with_relations`** on `TaskRepository`

### Changed

- Notion sync is now a DB-first, post-commit side effect — handlers no longer call `NotionService` directly
- `NotionService` marked as legacy in `dependencies.py`; `NotionSyncService` is the preferred integration point

---

## [0.2.0] — 2026

### Added

- **`ADMIN` user role** and full admin panel via Telegram bot
  - `AdminStates` FSM group with 11 states
  - **User list**: browse all registered users
  - **User detail**: view full profile (name, Telegram ID, role, executor type, join date)
  - **Change role**: 2-step flow — select role, then select executor type when role is EXECUTOR
  - **Delete user**: confirmation dialog; cascade-deletes all applicant tasks
  - **Create user**: 5-step guided form (first name → last name → Telegram ID → role → executor type)
  - **Task list**: admin overview of all tasks (up to 20 shown inline)
  - `_assert_admin()` guard function — protects every admin handler
- **`ExecutorType` enum** (`SYSADMIN`, `MASTER`) — added to `User` model as optional `type` column
  - `SYSADMIN` handles `SYSTEM` tasks (IT, computers, network, software)
  - `MASTER` handles `LOCAL` tasks (facilities, furniture, plumbing, lighting)
  - Enforced at creation and update: EXECUTOR role requires a non-null `type`; other roles require null
- **`NoExecutorError`** exception — raised when no executor of the required type is available
- **`UserService.get_executor_for_type(task_type)`** — strict executor selection (no fallback); raises `NoExecutorError`
- **`UserService.update_user_fields(user_id, data: UserUpdate)`** — partial update with role/type consistency validation
- **`UserService.delete_user(user_id)`** — cascades through tasks
- **User management API endpoints**:
  - `POST /api/users` — create user with role and optional executor type
  - `GET /api/users` — list all users
  - `PATCH /api/users/{user_id}` — partial update; changing away from EXECUTOR auto-clears `type`
- **`UserUpdate` Pydantic schema** — all fields optional; validates role/type consistency
- **`UserCreate` schema validation** — EXECUTOR requires `type`, non-EXECUTOR must not have `type`
- **`UserResponse` schema** — includes `type` field
- **Admin keyboard layouts** (`app/bot/keyboards/admin.py`)
- **Second Alembic migration** (`b1c3e7f2a894_add_executor_type_to_users.py`) — adds `type` column to `users`
- **`SUPERADMIN_TELEGRAM_ID` setting** — user matching this ID receives `ADMIN` role on first `/start`

### Changed

- Executor assignment moved from AI model to server business logic (`UserService.get_executor_for_type`)
- `get_or_create_user` auto-promotes superadmin to ADMIN role

---

## [0.1.0] — 2024-01-01

### Added

#### Project Setup

- Initial project structure with Clean Architecture
- Docker and Docker Compose configuration
- Alembic database migration setup
- Pydantic Settings for environment configuration

#### Database Layer

- SQLAlchemy 2.x async ORM models: `User` (APPLICANT/EXECUTOR roles), `Task` (full lifecycle)
- User and Task repositories with full CRUD
- Database session management with async support
- Initial Alembic migration (`a6ac8a5bb63b_initial.py`)

#### Services

- `UserService` — user management and role handling
- `TaskService` — task CRUD and lifecycle management
- `AIService` — OpenRouter-based ticket classification
- `NotionService` — Notion page CRUD (direct)
- Dependency injection helpers in `app/services/dependencies.py`

#### Telegram Bot

- FSM-based conversation flow with aiogram 3.x
- `ApplicantStates` — main menu, create request, my requests, confirm requests
- `ExecutorStates` — new tasks, my tasks, complete task, feedback input
- Keyboard layouts for Applicant and Executor
- Handlers: common (`/start`, `/help`, `/cancel`), applicant, executor

#### FastAPI REST API

- `GET /health` — health check
- `GET /api/tasks` — list tasks
- `GET /api/tasks/{id}` — get task
- `POST /api/tasks` — create task
- `PATCH /api/tasks/{id}/status` — update status
- Pydantic v2 schemas, exception handlers, Swagger/ReDoc

#### Logging and Error Handling

- Structured logging via `app/core/logging.py`
- Custom exception hierarchy: `AppException`, `ValidationError`, `NotFoundError`, `AuthenticationError`, `AuthorizationError`, `AIServiceError`, `NotionServiceError`, `TelegramServiceError`, `DatabaseError`
- Global exception handlers in FastAPI

### Supported Task Types

- **SYSTEM**: IT issues (computers, printers, network, software, servers)
- **LOCAL**: Facility issues (furniture, doors, lighting, plumbing)

### Known Limitations (at 0.1.0)

- FSM state stored in memory (`MemoryStorage`) — lost on restart
- Single executor per task type
- No task reassignment workflow
- No built-in API rate limiting
