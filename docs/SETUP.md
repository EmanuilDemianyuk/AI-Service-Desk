# Setup Instructions

This document provides step-by-step instructions to setup and run the HelpDesk Telegram Bot.

## Prerequisites

- Python 3.13 or later
- PostgreSQL 16 or later (can use Docker)
- Docker and Docker Compose (optional, for containerized setup)
- Telegram Bot Token (from BotFather)
- OpenRouter API Key (for AI classification)
- Notion Token and Database ID (optional, for Notion integration)

## Installation

### Option 1: Using Docker Compose (Recommended)

#### Step 1: Clone and Navigate to Project

```bash
cd "c:/Users/SSHarp/Desktop/Service Desk Agent/service-desk-bot"
```

#### Step 2: Configure Environment Variables

Copy the `.env.example` file to `.env` and fill in the required values:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
BOT_TOKEN=your_telegram_bot_token
OPENROUTER_API_KEY=your_openrouter_api_key
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_notion_database_id
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

This will:

- Start PostgreSQL database
- Build and start the FastAPI application
- Run the bot in polling mode

#### Step 4: Check Status

```bash
docker-compose ps
docker-compose logs -f app
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
source venv/Scripts/activate  # On Windows
# or
source venv/bin/activate  # On macOS/Linux
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

For local PostgreSQL, ensure it's running on localhost:5432

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

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/start` command
3. Send `/newbot` to create a new bot
4. Follow instructions to get your token
5. Copy token to `.env` file as `BOT_TOKEN`

### OpenRouter API Key

1. Visit [OpenRouter](https://openrouter.ai)
2. Sign up or log in
3. Go to API Keys section
4. Create new API key
5. Copy key to `.env` file as `OPENROUTER_API_KEY`

### Notion Integration (Optional)

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the token and set as `NOTION_TOKEN`
4. Create a database in Notion with the following columns:
   - Task ID (Number)
   - Title (Text)
   - Description (Text)
   - Type (Select: SYSTEM, LOCAL)
   - Priority (Select: LOW, MEDIUM, HIGH)
   - Status (Select: NEW, IN_PROGRESS, WAITING_APPLICANT, WAITING_EXECUTOR, DONE, CANCELLED)
   - Applicant (Text)
   - Executor (Text)
   - Feedback (Text)
   - Created At (Date)
   - Closed At (Date)
5. Copy database ID and set as `NOTION_DATABASE_ID`

---

## API Documentation

Once the application is running, access API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Available Endpoints

#### Health Check

- `GET /health` - Check if service is running

#### Tasks

- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{task_id}` - Get task by ID
- `POST /api/tasks` - Create new task
- `PATCH /api/tasks/{task_id}/status` - Update task status

---

## Bot Usage

### For Applicants

1. Start the bot: `/start`
2. Main menu options:
   - **Create Request** - Submit a new help request
   - **My Requests** - View your submitted requests
   - **Request Status** - Check status of a specific request

### For Executors

1. Start the bot: `/start`
2. Main menu options:
   - **New Tasks** - View and take new tasks
   - **My Tasks** - View tasks in progress
   - **Complete Task** - Mark task as complete with feedback

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'APPLICANT',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tasks Table

```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    notion_page_id VARCHAR(255),
    applicant_id INTEGER NOT NULL REFERENCES users(id),
    executor_id INTEGER REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP
);
```

---

## Task Status Lifecycle

```
NEW
├─> IN_PROGRESS (Executor takes task)
│   └─> WAITING_APPLICANT (Executor completes work)
│       ├─> DONE (Applicant confirms)
│       └─> IN_PROGRESS (Applicant rejects)
│           └─> WAITING_EXECUTOR (Back to executor)
│               └─> WAITING_APPLICANT (Executor completes again)
└─> CANCELLED (Task cancelled)
```

---

## Troubleshooting

### Bot not responding

1. Check if token is correct: `BOT_TOKEN` in `.env`
2. Check if bot is running: `docker-compose logs -f app`
3. Verify Telegram account can access bot

### Database connection error

1. Check PostgreSQL is running
2. Verify connection details in `.env`
3. Check firewall/security groups if using remote database

### AI classification failing

1. Verify OpenRouter API key is valid
2. Check rate limits on OpenRouter
3. Check internet connectivity

### Notion integration not working

1. Verify Notion token is valid
2. Verify database ID is correct
3. Ensure database has required columns

---

## Development

### Code Structure

```
app/
├── ai/              # AI classification service
├── bot/             # Telegram bot handlers
├── database/        # Database models and repositories
├── services/        # Business logic services
├── api/             # FastAPI routes
├── schemas/         # Pydantic models
├── config/          # Settings and configuration
├── core/            # Core utilities (logging)
├── exceptions/      # Custom exceptions
└── main.py          # FastAPI application entry point
```

### Running Tests

```bash
pytest
```

### Type Checking

```bash
mypy app/
```

### Linting

```bash
flake8 app/
black app/
```

---

## Production Deployment

### Using Gunicorn + Uvicorn

```bash
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Using Docker Compose with Nginx

Create `nginx.conf`:

```nginx
upstream api {
    server app:8000;
}

server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Update `docker-compose.yml` to include Nginx service.

### Environment Variables

For production, ensure:

- `DEBUG=false`
- `ENVIRONMENT=production`
- Use strong `POSTGRES_PASSWORD`
- Use valid bot token

---

## Monitoring and Logging

### View Logs

```bash
# Docker logs
docker-compose logs -f app

# Local logs
tail -f logs/app.log
```

### Error Logs

```bash
tail -f logs/error.log
```

---

## Support

For issues or questions, please check:

1. This setup guide
2. API documentation at `/docs`
3. Database migration logs
4. Application logs in `logs/` directory
