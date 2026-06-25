# HelpDesk AI Telegram Bot

An automated helpdesk ticket management system built with Telegram, AI classification, PostgreSQL, and Notion.

## Project Overview

The system automatically:

- Receives requests from employees through Telegram
- Classifies issues using AI (OpenRouter / qwen/qwen3-32b)
- Routes tasks to the correct executor (SYSADMIN for IT issues, MASTER for facility issues)
- Persists tasks in PostgreSQL database
- Mirrors tasks to Notion (optional)
- Tracks task statuses in real-time
- Collects executor feedback after task completion
- Handles applicant confirmation workflow

## Architecture

Two processes run separately:

- **FastAPI server** (`app/main.py`) — REST API + database schema initialization on startup
- **Bot runner** (`app/bot_runner.py`) — aiogram polling loop

```
Telegram Bot / FastAPI   ← Presentation
      ↓
Bot Handlers / Routes    ← Interface Adapters
      ↓
Services                 ← Business Logic
      ↓
Repositories             ← Data Access
      ↓
PostgreSQL / OpenRouter / Notion   ← External
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Docker & Docker Compose (optional)

### Using Docker Compose (Recommended)

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 2. Start all services
docker-compose up -d

# 3. Check status
docker-compose logs -f api
docker-compose logs -f bot
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 4. Run migrations
alembic upgrade head

# 5. Start API server (Terminal 1)
uvicorn app.main:app --reload

# 6. Start bot (Terminal 2)
python app/bot_runner.py
```

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

## Bot Usage

### Commands

| Command | Description |
|---|---|
| `/start` | Start the bot and go to role-specific main menu |
| `/help` | Show help message |
| `/cancel` | Cancel current operation |

### For Applicants (APPLICANT role)

| Button | Description |
|---|---|
| 📝 Створити запит | Submit a new helpdesk request with natural language description |
| 📋 Мої запити | View all submitted requests and their statuses |
| ✅ Підтвердити запит | Confirm or reject task completion (WAITING_APPLICANT tasks) |

**Request creation flow:**
1. Press «📝 Створити запит»
2. Describe the problem in natural language
3. AI classifies the request (type, priority, title, description in Ukrainian)
4. System finds the correct executor by type
5. Task is created and the applicant receives a confirmation with task details

### For Executors (EXECUTOR role)

| Button | Description |
|---|---|
| 🆕 Нові завдання | View new tasks filtered by executor specialization |
| ⏳ Мої завдання | View tasks currently IN_PROGRESS or WAITING_EXECUTOR |
| ✅ Позначити як завершене | Mark an IN_PROGRESS task as complete (requires a feedback comment) |

**Task execution flow:**
1. View new tasks in «🆕 Нові завдання» (filtered by executor type: SYSADMIN sees SYSTEM tasks, MASTER sees LOCAL tasks)
2. Open a task card and press «✅ Прийняти» to take it into progress
3. When done, press «✅ Позначити як завершене»
4. Enter a mandatory completion comment (feedback)
5. Task moves to WAITING_APPLICANT — applicant is asked to confirm

### For Admins (ADMIN role)

| Button | Description |
|---|---|
| 👥 Користувачі | Browse all users, view details, change roles, delete users |
| ➕ Створити користувача | Create a new user via multi-step form |
| 📋 Всі завдання | View all tasks in the system (last 20 shown) |

**User creation flow (4–5 steps):**
1. Enter first name
2. Enter last name
3. Enter Telegram ID (numeric, must not already exist)
4. Select role (APPLICANT / EXECUTOR / ADMIN)
5. If EXECUTOR: select executor type (SYSADMIN or MASTER)

**Role change flow:**
Open user → «Змінити роль» → select new role → if EXECUTOR, select type.
Changing a user away from EXECUTOR automatically clears their executor type.

## Task Lifecycle

```
NEW
├─> IN_PROGRESS           (executor accepts task via «🆕 Нові завдання»)
│   └─> WAITING_APPLICANT (executor marks complete with feedback)
│       ├─> DONE          (applicant confirms — task closed)
│       └─> IN_PROGRESS   (applicant rejects — feedback cleared, returned to executor)
└─> CANCELLED             (task cancelled, Notion page archived)
```

`WAITING_EXECUTOR` status is defined in the schema and is included in the executor's active task list alongside `IN_PROGRESS`.

## User Roles

| Role | Description |
|---|---|
| APPLICANT | Regular employee; creates requests, confirms task completion |
| EXECUTOR | Helpdesk specialist; accepts and resolves tasks |
| ADMIN | System administrator; manages users |

The first user whose Telegram ID matches `SUPERADMIN_TELEGRAM_ID` automatically receives the ADMIN role on first `/start`.

### Executor Types

| Type | Handles |
|---|---|
| SYSADMIN | IT tasks (computers, network, software, printers, servers) — `TaskType.SYSTEM` |
| MASTER | Facility tasks (furniture, plumbing, lighting, doors) — `TaskType.LOCAL` |

### Task Routing Logic

AI classifies the task type, then server-side logic selects the executor:
- `SYSTEM` → find first active executor with `ExecutorType.SYSADMIN`
- `LOCAL` → find first active executor with `ExecutorType.MASTER`

If no executor of the required type is registered, the applicant receives an error message asking them to contact the admin.

## Database Schema

### Users Table

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| telegram_id | BIGINT UNIQUE | |
| full_name | VARCHAR(255) | |
| username | VARCHAR(255) | nullable |
| role | ENUM | APPLICANT / EXECUTOR / ADMIN |
| type | ENUM | SYSADMIN / MASTER / NULL — only set for EXECUTOR role |
| is_active | BOOLEAN | default TRUE |
| created_at | TIMESTAMP | |

### Tasks Table

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| notion_page_id | VARCHAR(255) | nullable; set after Notion sync |
| applicant_id | INTEGER FK→users | CASCADE on delete |
| executor_id | INTEGER FK→users | nullable; SET NULL on delete |
| title | VARCHAR(255) | set by AI (Ukrainian) |
| description | TEXT | set by AI (Ukrainian); nullable |
| type | ENUM | SYSTEM / LOCAL |
| priority | ENUM | LOW / MEDIUM / HIGH |
| status | ENUM | NEW / IN_PROGRESS / WAITING_APPLICANT / WAITING_EXECUTOR / DONE / CANCELLED |
| feedback | TEXT | executor's completion comment; nullable |
| created_at | TIMESTAMP | |
| closed_at | TIMESTAMP | nullable; set when DONE or CANCELLED |

## AI Integration

Uses **OpenRouter API** with model `qwen/qwen3-32b`.

**Input**: Employee's natural language problem description

**Output**: JSON with classification (all text fields in Ukrainian)

```json
{
  "title": "Коротка назва проблеми",
  "description": "Детальний опис проблеми",
  "type": "SYSTEM або LOCAL",
  "priority": "LOW, MEDIUM або HIGH"
}
```

The AI does **not** determine the executor. Executor selection is server-side logic based on `type`.

**Task type rules:**
- `SYSTEM` — computers, printers, internet, Wi-Fi, network, software, servers, IT equipment
- `LOCAL` — furniture, doors, windows, lighting, plumbing, office infrastructure, facility maintenance

**Priority rules:**
- `HIGH` — work stopped, critical system unavailable, many users affected
- `MEDIUM` — work is impaired but possible
- `LOW` — minor inconvenience

## REST API

Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/users` | Create user; EXECUTOR requires `type=SYSADMIN\|MASTER` |
| GET | `/api/users` | List all users |
| PATCH | `/api/users/{user_id}` | Partial update; changing role away from EXECUTOR clears `type` |
| GET | `/api/tasks` | List all tasks (`{items: [...], total: N}`) |
| GET | `/api/tasks/{task_id}` | Get task by ID |
| POST | `/api/tasks` | Create a task |
| PATCH | `/api/tasks/{task_id}/status` | Update status, feedback, executor_id |
| POST | `/api/notion/sync` | Bulk-sync all DB tasks to Notion |

### API Examples

```bash
# Health check
curl http://localhost:8000/health

# List users
curl http://localhost:8000/api/users

# Create APPLICANT user
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "full_name": "John Doe", "role": "APPLICANT"}'

# Create EXECUTOR user
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 987654321, "full_name": "Jane Smith", "role": "EXECUTOR", "type": "SYSADMIN"}'

# Update user role
curl -X PATCH http://localhost:8000/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"role": "EXECUTOR", "type": "MASTER"}'

# List all tasks
curl http://localhost:8000/api/tasks

# Create task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "applicant_id": 1,
    "executor_id": 2,
    "title": "Принтер не друкує",
    "description": "Принтер на складі не може надрукувати документи",
    "type": "SYSTEM",
    "priority": "MEDIUM"
  }'

# Update task status
curl -X PATCH http://localhost:8000/api/tasks/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "IN_PROGRESS"}'

# Bulk sync to Notion
curl -X POST http://localhost:8000/api/notion/sync
```

## Notion Integration

Notion acts as a **read-only mirror** of the database. The database is the single source of truth.

| DB Operation | Notion Operation |
|---|---|
| `create_task` | Create Notion page; persist `notion_page_id` back to DB |
| `take_task` | Update Notion page |
| `complete_task` | Update Notion page |
| `confirm_task` | Update Notion page |
| `reject_task` | Update Notion page |
| `cancel_task` | Archive Notion page |
| `POST /api/notion/sync` | Bulk reconciliation: create/update all tasks; log orphaned pages |

Notion is **optional**. All Notion operations are silently skipped when `NOTION_TOKEN` or `NOTION_DATABASE_ID` are absent. Notion errors are logged but never block or roll back DB operations.

**Notion page properties:**

| Property | Type | Content |
|---|---|---|
| Task ID | title | DB task ID |
| Title | rich_text | Task title |
| Description | rich_text | Task description |
| Type | select | SYSTEM / LOCAL |
| Priority | select | LOW / MEDIUM / HIGH |
| Status | select | Current task status |
| Applicant | rich_text | Applicant's full name |
| Executor | rich_text | Executor's full name |
| Created At | date | ISO-8601 creation date |
| Feedback | rich_text | Executor's completion comment |
| Closed At | date | ISO-8601 closing date |

## Project Structure

```
app/
├── main.py                     # FastAPI app entry point
├── bot_runner.py               # Bot polling loop entry point
├── api/
│   └── routes.py               # FastAPI route handlers
├── bot/
│   ├── bot.py                  # Bot and dispatcher setup
│   ├── handlers/
│   │   ├── common.py           # /start, /help, /cancel, guard callbacks
│   │   ├── applicant.py        # Applicant workflow handlers
│   │   ├── executor.py         # Executor workflow handlers
│   │   └── admin.py            # Admin panel handlers
│   ├── keyboards/
│   │   ├── applicant.py        # Applicant keyboard layouts
│   │   ├── executor.py         # Executor keyboard layouts
│   │   ├── admin.py            # Admin keyboard layouts
│   │   └── localizer.py        # Ukrainian display text for statuses/priorities/types
│   ├── middleware/
│   │   ├── command_guard.py    # Guards commands during active input flows
│   │   └── nav_delete.py       # Deletes navigation messages from chat
│   └── states/
│       └── states.py           # FSM state groups + FLOW_STATES frozenset
├── config/
│   └── settings.py             # Pydantic BaseSettings — all env vars
├── core/
│   └── logging.py              # setup_logging() + get_logger()
├── database/
│   ├── base.py                 # SQLAlchemy engine + Base
│   ├── session.py              # get_db_session FastAPI dependency
│   ├── models/
│   │   ├── user.py             # User model, UserRole, ExecutorType enums
│   │   └── task.py             # Task model, TaskStatus, TaskType, TaskPriority enums
│   └── repositories/
│       ├── base.py             # Abstract BaseRepository
│       ├── user_repository.py  # User data access
│       └── task_repository.py  # Task data access
├── exceptions/
│   └── exceptions.py           # Custom exception hierarchy (AppException subclasses)
├── schemas/
│   └── schemas.py              # Pydantic request/response schemas
└── services/
    ├── ai_service.py           # OpenRouter ticket classification
    ├── notion_service.py       # Direct Notion CRUD (legacy)
    ├── notion_sync_service.py  # Centralised Notion sync (preferred)
    ├── task_service.py         # Task lifecycle + Notion sync side effects
    ├── user_service.py         # User CRUD, role management, executor selection
    └── dependencies.py         # Service factory functions for FastAPI DI

migrations/
├── env.py
└── versions/
    ├── a6ac8a5bb63b_initial.py
    └── b1c3e7f2a894_add_executor_type_to_users.py

scripts/
└── migrate_tasks_to_ukrainian.py
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
# Telegram Bot (required)
BOT_TOKEN=your_bot_token_here
SUPERADMIN_TELEGRAM_ID=your_telegram_id_here

# Database (required)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=helpdesk
POSTGRES_USER=helpdesk_user
POSTGRES_PASSWORD=secure_password_here

# FastAPI (optional, defaults shown)
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
ENVIRONMENT=development

# AI Provider (optional — AI classification disabled if absent)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Notion Integration (optional — Notion sync disabled if absent)
NOTION_TOKEN=your_notion_token_here
NOTION_DATABASE_ID=your_notion_database_id_here
```

### Required variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather |
| `SUPERADMIN_TELEGRAM_ID` | Telegram user ID that automatically gets ADMIN role on first `/start` |
| `POSTGRES_HOST` | PostgreSQL host |
| `POSTGRES_PORT` | PostgreSQL port (default: 5432) |
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |

### Optional variables

| Variable | Description | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key; AI classification disabled if absent | — |
| `NOTION_TOKEN` | Notion integration token; Notion sync disabled if absent | — |
| `NOTION_DATABASE_ID` | Notion database ID; Notion sync disabled if absent | — |
| `API_HOST` | FastAPI bind host | `0.0.0.0` |
| `API_PORT` | FastAPI bind port | `8000` |
| `DEBUG` | Enable debug mode | `false` |
| `ENVIRONMENT` | Environment name | `development` |

## Technology Stack

| Category | Technology |
|---|---|
| Language | Python 3.12 |
| Bot framework | aiogram 3.3.0 |
| REST API | FastAPI 0.104.1 |
| ASGI server | Uvicorn 0.24.0 |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0.23 (async) |
| Migrations | Alembic 1.13.0 |
| PG adapter | asyncpg + psycopg3 |
| Validation | Pydantic 2.5.0 |
| Settings | pydantic-settings 2.1.0 |
| AI API | OpenRouter (qwen/qwen3-32b) |
| Notion API | notion-client 2.2.1 |
| Logging | structlog 24.1.0 |
| Containerization | Docker + Docker Compose |

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (auto-generate from models)
alembic revision --autogenerate -m "description"

# Roll back one step
alembic downgrade -1
```

Migration history:
1. `a6ac8a5bb63b_initial` — creates `users` and `tasks` tables
2. `b1c3e7f2a894_add_executor_type_to_users` — adds `type` (ExecutorType) column to `users`

## Code Quality

```bash
bash format.sh    # black + isort
bash check.sh     # pytest + mypy + flake8 + formatting check
mypy app/
flake8 app/
pytest --cov=app
```

## Logging

Logs are written to:

- **Console** — INFO level and above
- **logs/app.log** — all logs (DEBUG and above)
- **logs/error.log** — ERROR logs only

```bash
# Docker
docker-compose logs -f api
docker-compose logs -f bot

# Local
tail -f logs/app.log
```

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions.

### Docker Compose (quick start)

```bash
docker-compose up -d
docker-compose logs -f api
docker-compose logs -f bot
```

### Manual deployment

```bash
# API server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Bot (separate process)
python app/bot_runner.py
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Architecture, data flow, design patterns
- [docs/SETUP.md](docs/SETUP.md) — Detailed setup instructions
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Production deployment guide
- [docs/INDEX.md](docs/INDEX.md) — Project file index
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

Proprietary — Service Desk Agent Project
