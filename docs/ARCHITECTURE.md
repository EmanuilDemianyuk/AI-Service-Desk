# Architecture Overview

This document describes the architecture and design patterns used in the HelpDesk Bot application.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Users                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ (aiogram)
                       ▼
┌─────────────────────────────────────────────────────────┐
│         Telegram Bot (Polling/Webhook)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Handlers Layer (FSM-based)                      │   │
│  │  ├─ Applicant Handlers                           │   │
│  │  ├─ Executor Handlers                            │   │
│  │  └─ Common Handlers                              │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Services   │ │   Services   │ │   Services   │
│              │ │              │ │              │
│ UserService  │ │ TaskService  │ │ AIService    │
│ TaskService  │ │ AIService    │ │ NotionService│
│              │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│         Repositories (Data Access Layer)                │
│  ┌──────────────────────────────────────────────────┐   │
│  │  UserRepository      │  TaskRepository           │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ OpenRouter   │ │    Notion    │
│   Database   │ │   (AI API)   │ │    (CMS)     │
└──────────────┘ └──────────────┘ └──────────────┘

┌──────────────────────────────────────────────────────────┐
│         FastAPI REST API                                 │
│  ├─ Health Check Endpoint                                │
│  ├─ Task CRUD Endpoints                                  │
│  └─ Swagger/ReDoc Documentation                          │
└──────────────────────────────────────────────────────────┘
```

---

## Design Patterns

### 1. Repository Pattern

**Purpose**: Abstract database access and provide a uniform interface.

**Implementation**:

```python
# In app/database/repositories/user_repository.py
class UserRepository(BaseRepository):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        # Database access logic
        pass
```

**Benefits**:

- Decouples business logic from database operations
- Enables easy testing with mock repositories
- Centralized query logic

---

### 2. Service Layer Pattern

**Purpose**: Encapsulate business logic separate from presentation and data layers.

**Implementation**:

```python
# In app/services/user_service.py
class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def get_or_create_user(self, telegram_id: int, ...) -> User:
        # Business logic
        pass
```

**Benefits**:

- Clear separation of concerns
- Reusable business logic across handlers and API
- Easy to test

---

### 3. Dependency Injection

**Purpose**: Manage service dependencies and enable loose coupling.

**Implementation**:

```python
# In app/services/dependencies.py
async def get_user_service(session: AsyncSession) -> UserService:
    repository = UserRepository(session)
    return UserService(repository)

# In FastAPI routes
@router.get("/tasks")
async def get_tasks(
    session: AsyncSession = Depends(get_db_session),
):
    pass
```

**Benefits**:

- Easy to swap implementations (e.g., for testing)
- Clear dependency requirements
- Automatic lifecycle management

---

### 4. Finite State Machine (FSM)

**Purpose**: Manage bot conversation flow and state transitions.

**Implementation**:

```python
# In app/bot/states/states.py
class ApplicantStates(StatesGroup):
    main_menu = State()
    create_request = State()
    request_description = State()

# In handlers
@router.message(ApplicantStates.main_menu, F.text == "📝 Create Request")
async def create_request_start(message: Message, state: FSMContext):
    await state.set_state(ApplicantStates.request_description)
```

**Benefits**:

- Prevents invalid state transitions
- Clear flow logic
- State data persistence

---

### 5. Clean Architecture

**Layers** (from innermost to outermost):

1. **Entities** - Domain models (User, Task, enums)
2. **Use Cases** - Business logic (Services)
3. **Interface Adapters** - Repositories, API routes, Bot handlers
4. **External Interfaces** - Database, APIs, Telegram

**Benefits**:

- Independent of frameworks
- Testable business logic
- Easy to swap implementations
- Clear data flow

---

## Data Flow

### Task Creation Flow

```
User sends message to bot
    ↓
Handler receives message → ApplicantStates.request_description
    ↓
Handler calls UserService.get_user_by_telegram_id()
    ↓
UserService queries UserRepository
    ↓
Repository executes SQL query
    ↓
User data returned to handler
    ↓
Handler calls AIService.classify_ticket()
    ↓
AIService calls OpenRouter API
    ↓
AI classification returned (type, priority, executor)
    ↓
Handler calls TaskService.create_task()
    ↓
TaskService calls TaskRepository.create()
    ↓
Task saved to PostgreSQL database
    ↓
Handler calls NotionService.create_task_page()
    ↓
Notion page created (optional)
    ↓
Executor notified via bot
    ↓
Response sent to applicant
```

---

## Database Schema

### ERD (Entity Relationship Diagram)

```
Users Table
┌─────────────────────────────┐
│ id (PK)                     │
│ telegram_id (UNIQUE)        │
│ full_name                   │
│ username                    │
│ role (APPLICANT/EXECUTOR)   │
│ is_active                   │
│ created_at                  │
└─────────────────────────────┘
          ▲         ▲
          │         │
    (1:N) │         │ (1:N)
          │         │
          │         │
Tasks Table
┌─────────────────────────────┐
│ id (PK)                     │
│ applicant_id (FK) ──────────┤
│ executor_id (FK) ───────────┤
│ title                       │
│ description                 │
│ type (SYSTEM/LOCAL)         │
│ priority (LOW/MEDIUM/HIGH)  │
│ status (NEW/IN_PROGRESS...)│
│ feedback                    │
│ notion_page_id              │
│ created_at                  │
│ closed_at                   │
└─────────────────────────────┘
```

---

## Service Responsibilities

### UserService

- User creation and retrieval
- Role management
- Executor assignment

### TaskService

- Task CRUD operations
- Status transitions
- Task lifecycle management

### AIService

- Ticket classification
- Title and description generation
- Priority determination

### NotionService

- Notion page creation
- Status synchronization
- Feedback persistence

---

## API Routes

### Health Check

```
GET /health
Response: {"status": "healthy", "message": "Service is running"}
```

### List Tasks

```
GET /api/tasks
Response: {"items": [...], "total": N}
```

### Get Task

```
GET /api/tasks/{task_id}
Response: {TaskResponse}
```

### Create Task

```
POST /api/tasks
Body: {TaskCreate}
Response: {TaskResponse}
Status: 201 Created
```

### Update Task Status

```
PATCH /api/tasks/{task_id}/status
Body: {TaskUpdate}
Response: {TaskResponse}
```

---

## Error Handling

### Exception Hierarchy

```
Exception
├─ AppException (Custom)
│  ├─ ValidationError
│  ├─ NotFoundError
│  ├─ AuthenticationError
│  ├─ AuthorizationError
│  ├─ AIServiceError
│  ├─ NotionServiceError
│  ├─ TelegramServiceError
│  └─ DatabaseError
```

### Error Responses

```json
{
  "error": "NotFoundError",
  "detail": "User 123 not found",
  "code": "USER_NOT_FOUND"
}
```

---

## Logging

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical system errors

### Log Output

- **Console**: INFO and above
- **File** (`logs/app.log`): DEBUG and above
- **Error File** (`logs/error.log`): ERROR and above

---

## Security Considerations

1. **Environment Variables**: Sensitive data stored in `.env`
2. **Database Credentials**: Never hardcoded
3. **API Keys**: Not exposed in logs
4. **Input Validation**: Pydantic validation
5. **Error Handling**: Generic error messages to users

---

## Performance Considerations

1. **Async Operations**: All I/O operations are async
2. **Connection Pooling**: SQLAlchemy connection pool
3. **Database Indexes**: On frequently queried columns
4. **Caching**: Potential for Redis caching
5. **Rate Limiting**: Recommended for production

---

## Future Enhancements

1. **Authentication**: JWT-based API authentication
2. **Authorization**: Role-based access control
3. **Caching**: Redis for frequently accessed data
4. **Message Queue**: Celery for async tasks
5. **Webhooks**: Instead of polling for bot updates
6. **Analytics**: Task statistics and metrics
7. **Notifications**: Email/SMS notifications
8. **Multi-Executor**: Load balancing across executors
