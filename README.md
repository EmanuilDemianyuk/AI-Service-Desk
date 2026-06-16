# 🤖 HelpDesk AI Telegram Bot

An automated helpdesk ticket management system built with Telegram, AI classification, PostgreSQL, and Notion.

## 📋 Project Overview

The system automatically:

- ✅ Receives requests from employees through Telegram
- ✅ Classifies issues using AI (OpenRouter)
- ✅ Assigns appropriate executors automatically
- ✅ Creates tasks in PostgreSQL database
- ✅ Syncs tasks with Notion (optional)
- ✅ Tracks task statuses in real-time
- ✅ Collects executor feedback after completion
- ✅ Manages applicant confirmation workflow

## 🎯 MVP Scope

### Implemented Features

✅ Telegram Bot with FSM-based conversation flow  
✅ AI-based ticket classification (SYSTEM/LOCAL)  
✅ PostgreSQL database with async ORM  
✅ Notion integration for task tracking  
✅ Task status management (6 states)  
✅ Applicant confirmation workflow  
✅ Executor feedback collection  
✅ REST API with FastAPI  
✅ Clean Architecture with Repository Pattern  
✅ Full async/await implementation  
✅ Comprehensive type hints  
✅ Production-ready error handling  
✅ Structured logging  
✅ Docker & Docker Compose support

### Out of Scope (MVP)

- Chat between applicant and executor
- Photo/file attachments
- Voice messages
- Multiple executors per task
- SLA management
- Task escalation
- Task comments
- Reminder notifications

## 🏗️ Architecture

The project follows **Clean Architecture** principles with clear separation of concerns:

```
Presentation Layer (Telegram Bot, FastAPI)
        ↓
Interface Adapters (Handlers, Routes)
        ↓
Application Layer (Services)
        ↓
Domain Layer (Models, Entities)
        ↓
External Interfaces (Database, APIs)
```

[See ARCHITECTURE.md for detailed architecture documentation](ARCHITECTURE.md)

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 16+
- Docker & Docker Compose (optional)

### Using Docker Compose (Recommended)

```bash
# 1. Clone and navigate to project
cd "Service Desk Agent/service-desk-bot"

# 2. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 3. Start services
docker-compose up -d

# 4. Check status
docker-compose logs -f app
```

### Local Development

```bash
# 1. Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

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

[See SETUP.md for detailed setup instructions](SETUP.md)

## 📱 Bot Usage

### For Applicants

1. Start bot: `/start`
2. Create requests with natural language descriptions
3. AI automatically classifies the issue
4. Track request status
5. Confirm completion

### For Executors

1. Start bot: `/start`
2. View new tasks assigned
3. Take tasks into progress
4. Complete work and provide feedback
5. Receive applicant confirmation

## 🔄 Task Lifecycle

```
NEW
├─→ IN_PROGRESS (Executor takes task)
│   └─→ WAITING_APPLICANT (Executor completes)
│       ├─→ DONE (Applicant confirms)
│       └─→ IN_PROGRESS (Applicant rejects)
│           └─→ WAITING_EXECUTOR (Back to executor)
└─→ CANCELLED (Task cancelled)
```

## 💾 Database Schema

### Users Table

```sql
id SERIAL PRIMARY KEY
telegram_id BIGINT UNIQUE NOT NULL
full_name VARCHAR(255) NOT NULL
username VARCHAR(255)
role VARCHAR(50) DEFAULT 'APPLICANT'
is_active BOOLEAN DEFAULT TRUE
created_at TIMESTAMP DEFAULT NOW()
```

### Tasks Table

```sql
id SERIAL PRIMARY KEY
applicant_id INTEGER NOT NULL REFERENCES users(id)
executor_id INTEGER REFERENCES users(id)
title TEXT NOT NULL
description TEXT
type VARCHAR(50) NOT NULL  -- SYSTEM or LOCAL
priority VARCHAR(50) NOT NULL  -- LOW, MEDIUM, HIGH
status VARCHAR(50) NOT NULL  -- See lifecycle above
feedback TEXT
notion_page_id VARCHAR(255)
created_at TIMESTAMP DEFAULT NOW()
closed_at TIMESTAMP
```

## 🤖 AI Integration

Uses OpenRouter API to classify tickets:

**Input**: Natural language problem description  
**Output**: JSON with classification

```json
{
  "title": "Brief issue title",
  "description": "Detailed description",
  "type": "SYSTEM or LOCAL",
  "priority": "LOW, MEDIUM, or HIGH",
  "executor": "SysAdmin or Caretaker"
}
```

**Task Type Assignment**:

- **SYSTEM** → SysAdmin (computers, printers, network, software, servers)
- **LOCAL** → Caretaker (furniture, doors, lighting, facility maintenance)

## 📡 REST API

Access Swagger UI at: http://localhost:8000/docs

### Endpoints

| Method | Endpoint                      | Description        |
| ------ | ----------------------------- | ------------------ |
| GET    | `/health`                     | Health check       |
| GET    | `/api/tasks`                  | List all tasks     |
| GET    | `/api/tasks/{task_id}`        | Get task by ID     |
| POST   | `/api/tasks`                  | Create new task    |
| PATCH  | `/api/tasks/{task_id}/status` | Update task status |

## 🧬 Code Structure

```
app/
├── ai/                    # AI classification service
│   ├── ai_service.py
│   └── __init__.py
├── bot/                   # Telegram bot
│   ├── handlers/          # Message/callback handlers
│   │   ├── common.py
│   │   ├── applicant.py
│   │   ├── executor.py
│   │   └── __init__.py
│   ├── keyboards/         # Inline buttons
│   │   ├── applicant.py
│   │   ├── executor.py
│   │   └── __init__.py
│   ├── states/            # FSM states
│   │   ├── states.py
│   │   └── __init__.py
│   ├── bot.py
│   └── __init__.py
├── database/              # Data layer
│   ├── models/            # ORM models
│   │   ├── user.py
│   │   ├── task.py
│   │   └── __init__.py
│   ├── repositories/      # Data access
│   │   ├── base.py
│   │   ├── user_repository.py
│   │   ├── task_repository.py
│   │   └── __init__.py
│   ├── base.py            # SQLAlchemy setup
│   ├── session.py
│   └── __init__.py
├── services/              # Business logic
│   ├── user_service.py
│   ├── task_service.py
│   ├── ai_service.py
│   ├── notion_service.py
│   ├── dependencies.py
│   └── __init__.py
├── api/                   # FastAPI routes
│   ├── routes.py
│   └── __init__.py
├── schemas/               # Pydantic models
│   ├── schemas.py
│   └── __init__.py
├── config/                # Configuration
│   ├── settings.py
│   └── __init__.py
├── core/                  # Core utilities
│   ├── logging.py
│   └── __init__.py
├── exceptions/            # Custom exceptions
│   ├── exceptions.py
│   └── __init__.py
├── main.py                # FastAPI app
├── bot_runner.py          # Bot entry point
└── __init__.py
migrations/               # Alembic migrations
├── env.py
├── versions/
│   └── 001_initial.py
└── __init__.py
```

## 🏭 Design Patterns Used

- **Repository Pattern**: Data access abstraction
- **Service Layer**: Business logic encapsulation
- **Dependency Injection**: Loose coupling
- **Finite State Machine**: Bot conversation flow
- **Clean Architecture**: Clear separation of concerns

## ⚙️ Technology Stack

### Backend

- **Python 3.13**: Language
- **FastAPI 0.104.1**: REST API framework
- **Uvicorn 0.24.0**: ASGI server
- **aiogram 3.3.0**: Telegram bot framework

### Database

- **PostgreSQL 16**: Primary database
- **SQLAlchemy 2.0.23**: Async ORM
- **Alembic 1.13.0**: Migrations
- **psycopg 3.17.0**: PostgreSQL adapter

### Data & Config

- **Pydantic 2.5.0**: Data validation
- **Pydantic Settings 2.1.0**: Configuration management
- **python-dotenv 1.0.0**: Environment variables

### External APIs

- **OpenRouter**: AI classification
- **Notion API**: Task management
- **Telegram Bot API**: User interface

### DevOps

- **Docker**: Containerization
- **Docker Compose**: Orchestration

### Logging & Monitoring

- **structlog 24.1.0**: Structured logging
- **python-json-logger 2.0.7**: JSON logs

## 🔐 Configuration

Create `.env` file from `.env.example`:

```env
# Telegram
BOT_TOKEN=your_bot_token

# AI Provider
OPENROUTER_API_KEY=your_api_key

# Notion (optional)
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=helpdesk
POSTGRES_USER=helpdesk_user
POSTGRES_PASSWORD=secure_password

# App
DEBUG=false
ENVIRONMENT=production
```

## 📝 API Examples

### Get All Tasks

```bash
curl http://localhost:8000/api/tasks
```

### Get Single Task

```bash
curl http://localhost:8000/api/tasks/1
```

### Create Task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "applicant_id": 1,
    "executor_id": 2,
    "title": "Printer not working",
    "description": "Warehouse printer unable to print",
    "type": "SYSTEM",
    "priority": "MEDIUM"
  }'
```

### Update Task Status

```bash
curl -X PATCH http://localhost:8000/api/tasks/1/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "IN_PROGRESS"
  }'
```

## 🧪 Testing

Run tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app
```

## 📊 Logging

Logs are written to:

- **Console**: INFO level and above
- **logs/app.log**: All logs (DEBUG and above)
- **logs/error.log**: Error logs only

View logs:

```bash
# Docker
docker-compose logs -f app

# Local
tail -f logs/app.log
```

## 🚢 Deployment

### Docker Compose (Recommended)

```bash
docker-compose -f docker-compose.yml up -d
```

### Manual Deployment

```bash
# Install production requirements
pip install gunicorn

# Run with Gunicorn
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## 🔍 Monitoring & Logs

Health check:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "message": "Service is running"
}
```

## 📚 Documentation

- [SETUP.md](SETUP.md) - Detailed setup instructions
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture documentation
- API Docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

## ✅ Requirements Met

- ✅ Production-ready code
- ✅ Python 3.13
- ✅ FastAPI with async endpoints
- ✅ aiogram 3.x bot framework
- ✅ PostgreSQL with async ORM
- ✅ SQLAlchemy 2.x with AsyncSession
- ✅ Alembic migrations
- ✅ Pydantic v2 with Settings
- ✅ Dependency injection
- ✅ Repository pattern
- ✅ Service layer pattern
- ✅ Structured logging
- ✅ Environment variables via Pydantic
- ✅ Full async/await
- ✅ Complete type hints
- ✅ Clean Architecture
- ✅ SOLID principles
- ✅ Docker & Docker Compose support
- ✅ Comprehensive error handling
- ✅ Notion integration
- ✅ AI classification

## 🤝 Contributing

1. Create a feature branch
2. Make changes
3. Run tests and linting
4. Submit pull request

## 📄 License

Proprietary - Service Desk Agent Project

## 👥 Support

For issues, questions, or contributions, please refer to the documentation or create an issue in the project repository.
