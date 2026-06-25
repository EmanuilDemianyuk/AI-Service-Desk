# Setup Instructions

This document provides step-by-step instructions to setup and run the HelpDesk Telegram Bot.

## Prerequisites

- Python 3.12 or later
- PostgreSQL 16 or later (can use Docker)
- Docker and Docker Compose (optional, for containerized setup)
- Telegram Bot Token (from BotFather)
- OpenRouter API Key (for AI classification)
- Notion Token and Database ID (optional)

## Installation

### Option 1: Using Docker Compose (Recommended)

#### Step 1: Clone and Navigate to Project

```bash
cd service-desk-bot
```

#### Step 2: Configure Environment Variables

Copy the `.env.example` file to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
BOT_TOKEN=your_telegram_bot_token
SUPERADMIN_TELEGRAM_ID=123456789
OPENROUTER_API_KEY=your_openrouter_api_key
NOTION_TOKEN=your_notion_token          # optional
NOTION_DATABASE_ID=your_database_id     # optional
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=helpdesk
POSTGRES_USER=helpdesk_user
POSTGRES_PASSWORD=your_secure_password
DEBUG=false
ENVIRONMENT=production
```

#### Step 3: Start Services

```bash
docker-compose up -d
```

#### Step 4: Check Status

```bash
docker-compose ps
docker-compose logs -f api
docker-compose logs -f bot
```

#### Step 5: Stop Services

```bash
docker-compose down
```

---

### Option 2: Local Development Setup

#### Step 1: Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate      # Windows
# or
source venv/bin/activate   # macOS/Linux
```

#### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

#### Step 4: Run Database Migrations

```bash
alembic upgrade head
```

#### Step 5: Start the Application

In one terminal, start the FastAPI server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal, start the bot:

```bash
python app/bot_runner.py
```

---

## Configuration Details

### Required Variables

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/botfather) |
| `SUPERADMIN_TELEGRAM_ID` | Numeric Telegram user ID. The first `/start` from this account grants `ADMIN` role automatically. |
| `POSTGRES_HOST` | PostgreSQL host (default: `localhost`) |
| `POSTGRES_PORT` | PostgreSQL port (default: `5432`) |
| `POSTGRES_DB` | Database name (default: `helpdesk`) |
| `POSTGRES_USER` | Database user (default: `helpdesk_user`) |
| `POSTGRES_PASSWORD` | Database password |

### Optional Variables

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | AI classification key. If absent, `/classify_ticket` raises `AIServiceError`. |
| `NOTION_TOKEN` | Notion integration token. If absent, all Notion operations silently no-op. |
| `NOTION_DATABASE_ID` | Target Notion database. Required together with `NOTION_TOKEN`. |
| `DEBUG` | `true` / `false` (default: `false`) |
| `ENVIRONMENT` | `development` / `production` (default: `development`) |

### Getting Credentials

**Telegram Bot Token**:
1. Open Telegram → [@BotFather](https://t.me/botfather)
2. Send `/newbot`, follow instructions
3. Copy the token to `BOT_TOKEN`

**Your Telegram ID** (for `SUPERADMIN_TELEGRAM_ID`):
- Send any message to [@userinfobot](https://t.me/userinfobot) — it replies with your numeric ID.

**OpenRouter API Key**:
1. Visit [openrouter.ai](https://openrouter.ai)
2. Sign up → API Keys → Create key
3. Copy to `OPENROUTER_API_KEY`

**Notion Integration** (Optional):
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Create integration → copy token to `NOTION_TOKEN`
3. Create a Notion database with these properties:

| Property | Type | Values |
|---|---|---|
| Task ID | Title | — |
| Title | Rich Text | — |
| Description | Rich Text | — |
| Type | Select | SYSTEM, LOCAL |
| Priority | Select | LOW, MEDIUM, HIGH |
| Status | Select | NEW, IN_PROGRESS, WAITING_APPLICANT, WAITING_EXECUTOR, DONE, CANCELLED |
| Applicant | Rich Text | — |
| Executor | Rich Text | — |
| Feedback | Rich Text | — |
| Created At | Date | — |

4. Share the database with your integration, copy the database ID to `NOTION_DATABASE_ID`

---

## API Documentation

Once the application is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Available Endpoints

#### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |

#### Users

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/users` | Create user. EXECUTOR role requires `type=SYSADMIN\|MASTER` |
| `GET` | `/api/users` | List all users |
| `PATCH` | `/api/users/{user_id}` | Partial update. Changing from EXECUTOR clears `type` automatically |

#### Tasks

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/tasks` | List all tasks |
| `GET` | `/api/tasks/{task_id}` | Get task by ID |
| `POST` | `/api/tasks` | Create task |
| `PATCH` | `/api/tasks/{task_id}/status` | Update task status, feedback, or executor |

#### Notion

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/notion/sync` | Bulk-sync all DB tasks to Notion |

---

## Bot Usage

### Roles

| Role | Description |
|---|---|
| **Applicant** | Creates requests, monitors status, confirms completion |
| **Executor** | Processes assigned tasks; specialization is either `SYSADMIN` (IT) or `MASTER` (facilities) |
| **Admin** | Manages users and monitors all tasks. The first user matching `SUPERADMIN_TELEGRAM_ID` is auto-promoted on first `/start`. |

### For Applicants

1. Send `/start` → applicant main menu appears
2. Menu options:
   - **📝 Створити запит** — describe the problem; AI classifies it and assigns the right executor
   - **📋 Мої запити** — browse all your submitted requests
   - **✅ Підтвердити запит** — review and confirm/reject tasks marked as completed by the executor

### For Executors

Executor specialization determines which tasks appear:
- `SYSADMIN` → sees only `SYSTEM` tasks (IT: computers, network, software)
- `MASTER` → sees only `LOCAL` tasks (facilities: furniture, plumbing, lighting)

1. Send `/start` → executor main menu appears
2. Menu options:
   - **🆕 Нові завдання** — view unassigned tasks matching your specialization; tap a task to review details before accepting
   - **⏳ Мої завдання** — tasks currently assigned to you (IN_PROGRESS or WAITING_EXECUTOR)
   - **✅ Позначити як завершене** — select an IN_PROGRESS task, add a comment, and send it for applicant confirmation

### For Admins

1. Send `/start` → admin main menu appears
2. Menu options:
   - **👥 Користувачі** — browse all users; tap a user to view details, change role, or delete
   - **➕ Створити користувача** — 5-step form: first name → last name → Telegram ID → role → executor type (if EXECUTOR)
   - **📋 Всі завдання** — overview of all tasks (up to 20 shown, with count of remaining)

### Common Commands

| Command | Description |
|---|---|
| `/start` | Open the role-specific main menu |
| `/help` | Show available commands |
| `/cancel` | Cancel the current multi-step operation |

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name   VARCHAR(255) NOT NULL,
    username    VARCHAR(255),
    role        VARCHAR(50) NOT NULL DEFAULT 'APPLICANT', -- APPLICANT | EXECUTOR | ADMIN
    type        VARCHAR(50),                               -- SYSADMIN | MASTER | NULL
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

> `type` is only set (and required) when `role = 'EXECUTOR'`.

### Tasks Table

```sql
CREATE TABLE tasks (
    id             SERIAL PRIMARY KEY,
    notion_page_id VARCHAR(255),
    applicant_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    executor_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    title          VARCHAR(255) NOT NULL,
    description    TEXT,
    type           VARCHAR(50) NOT NULL,  -- SYSTEM | LOCAL
    priority       VARCHAR(50) NOT NULL,  -- LOW | MEDIUM | HIGH
    status         VARCHAR(50) NOT NULL,  -- NEW | IN_PROGRESS | ... | DONE | CANCELLED
    feedback       TEXT,
    created_at     TIMESTAMP DEFAULT NOW(),
    closed_at      TIMESTAMP
);
```

---

## Task Status Lifecycle

```
NEW
├─> IN_PROGRESS         (executor takes the task)
│   └─> WAITING_APPLICANT (executor marks complete with feedback)
│       ├─> DONE          (applicant confirms)
│       └─> IN_PROGRESS   (applicant rejects — feedback cleared)
└─> CANCELLED
```

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback one step
alembic downgrade -1
```

Current migrations in `migrations/versions/`:
- `a6ac8a5bb63b_initial.py` — initial schema (users + tasks)
- `b1c3e7f2a894_add_executor_type_to_users.py` — adds `type` column to `users`

---

## Code Quality

```bash
bash format.sh    # black + isort
bash check.sh     # pytest + mypy + flake8 + formatting check
mypy app/
flake8 app/
pytest --cov=app
```

---

## Troubleshooting

### Bot not responding

1. Verify `BOT_TOKEN` in `.env`
2. Check logs: `docker-compose logs -f bot`
3. Confirm the Telegram account can reach the bot

### Database connection error

1. Verify PostgreSQL is running
2. Check `POSTGRES_*` values in `.env`
3. Run `alembic upgrade head` to ensure schema is up to date

### AI classification failing

1. Verify `OPENROUTER_API_KEY` is valid
2. Check OpenRouter rate limits and account balance
3. Check internet connectivity from the container/server

### Notion sync not working

1. Verify `NOTION_TOKEN` and `NOTION_DATABASE_ID` are set
2. Ensure the integration has access to the database in Notion
3. Verify all required database properties exist (see Notion Integration section above)
4. Check logs for `Notion sync failed` entries
5. Use `POST /api/notion/sync` for a manual bulk sync

### No executor available error

If a request fails with "наразі відсутній виконавець":
1. An executor of the required type (`SYSADMIN` or `MASTER`) must be registered in the system
2. Use the admin panel or `POST /api/users` to create one with the correct `type`
