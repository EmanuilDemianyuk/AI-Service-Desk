# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-01

### Added

#### Project Setup

- Initial project structure with Clean Architecture
- Docker and Docker Compose configuration
- Alembic database migration setup
- Pydantic Settings for environment configuration
- Comprehensive requirements.txt and pyproject.toml
- .gitignore and .dockerignore files

#### Database Layer

- SQLAlchemy 2.x async ORM models
  - User model with roles (APPLICANT, EXECUTOR)
  - Task model with lifecycle statuses
- User and Task repositories with full CRUD operations
- Database session management with async support
- Initial Alembic migration creating users and tasks tables
- Indexes on frequently queried columns

#### Services

- UserService with user management and role handling
- TaskService with full task lifecycle management
- AIService for OpenRouter-based ticket classification
- NotionService for Notion database integration
- Dependency injection setup for service provisioning

#### Telegram Bot

- FSM-based conversation flow with aiogram 3.x
  - ApplicantStates: main menu, create request, check status
  - ExecutorStates: new tasks, my tasks, complete task
- Keyboard layouts for Applicant and Executor roles
- Handlers for common bot operations
  - Applicant handlers for creating and tracking requests
  - Executor handlers for task management
  - Common handlers for /start, /help, /cancel commands
- Bot setup and initialization with command registration

#### FastAPI REST API

- Health check endpoint
- Task CRUD endpoints
  - GET /api/tasks - list all tasks
  - GET /api/tasks/{task_id} - get single task
  - POST /api/tasks - create task
  - PATCH /api/tasks/{task_id}/status - update status
- Pydantic schemas for request/response validation
- Exception handling with custom error responses
- Database session management with async support
- Swagger UI and ReDoc documentation

#### Logging and Monitoring

- Structured logging with structlog
- JSON logging for production
- Rotating file handlers for logs
- Separate error log file
- Console output for development
- Debug logging in development mode

#### Error Handling

- Custom exception hierarchy
  - AppException (base)
  - ValidationError
  - NotFoundError
  - AuthenticationError
  - AuthorizationError
  - AIServiceError
  - NotionServiceError
  - TelegramServiceError
  - DatabaseError
- Global exception handlers in FastAPI
- Graceful error responses with error codes

#### Documentation

- Comprehensive README.md
- SETUP.md with detailed installation instructions
- ARCHITECTURE.md explaining system design
- DEPLOYMENT.md for production deployment
- CONTRIBUTING.md for development guidelines
- This CHANGELOG.md

### Technical Implementation

- Full async/await implementation throughout
- Complete type hints (Python 3.13 syntax)
- Repository pattern for data access abstraction
- Service layer for business logic
- Dependency injection for loose coupling
- FSM for bot conversation management
- Clean separation of concerns
- Production-ready error handling
- Comprehensive logging
- Docker containerization
- Database migrations

### Supported Task Types

- **SYSTEM**: Assigned to SysAdmin
  - Computers, printers, network, internet, software, servers, IT equipment
- **LOCAL**: Assigned to Caretaker
  - Furniture, doors, lighting, facility maintenance, office infrastructure

### Task Statuses

- NEW: Initial state
- IN_PROGRESS: Executor working on task
- WAITING_APPLICANT: Executor completed, awaiting confirmation
- WAITING_EXECUTOR: Applicant rejected, executor resumes
- DONE: Task completed and confirmed
- CANCELLED: Task cancelled

### Integration

- **Telegram**: aiogram 3.x for bot functionality
- **AI Classification**: OpenRouter API
- **Database**: PostgreSQL 16 with async support
- **Notion**: Optional integration for task sync
- **API Framework**: FastAPI with async support

### Configuration

- Environment-based configuration via Pydantic Settings
- Support for .env files
- Production and development modes
- Debug mode support

### DevOps

- Docker containerization
- Docker Compose orchestration
- Alembic database migrations
- Health check endpoints
- Structured logging setup
- Error tracking

### Known Limitations

- Bot polling mode (webhook available for production)
- Single executor per task type
- No task reassignment workflow
- No built-in rate limiting on API
- Memory-based FSM storage (recommend Redis for production)

### Next Steps (Future Versions)

- [ ] Webhook mode for bot updates
- [ ] Redis caching layer
- [ ] Multiple executors per task type
- [ ] Task escalation workflow
- [ ] Email/SMS notifications
- [ ] Analytics dashboard
- [ ] Admin panel
- [ ] SLA management
- [ ] Audit logging
- [ ] API authentication (JWT)

## Notes

This is the initial MVP release implementing core helpdesk functionality as specified in requirements.
