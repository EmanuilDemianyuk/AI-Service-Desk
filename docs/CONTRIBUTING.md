# Contributing Guidelines

## Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd service-desk-bot
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Setup Environment

```bash
cp .env.example .env
# Edit .env with your development values
```

### 5. Run Migrations

```bash
alembic upgrade head
```

---

## Development Workflow

### Before Making Changes

1. Create feature branch: `git checkout -b feature/description`
2. Keep branch up to date with `main`
3. Write tests for new features

### Making Changes

1. Follow PEP 8 style guide
2. Add type hints to all function signatures
3. Keep docstrings to one line — only document **why**, not **what**
4. Update relevant documentation

### Code Quality

```bash
bash format.sh   # black + isort
bash check.sh    # pytest + mypy + flake8 + formatting check
mypy app/
flake8 app/
pytest --cov=app
```

---

## Commit Guidelines

Use conventional commits:

```
feat: add task escalation workflow
fix: correct executor type validation
docs: update architecture diagram
test: add user service integration tests
```

Reference issues: `Fixes #123`

---

## Code Style

### Naming Conventions

```python
EXECUTOR_TIMEOUT = 3600          # constants: UPPER_SNAKE_CASE
def get_user_by_telegram_id(...) # functions: snake_case
class UserService:               # classes: PascalCase
def _validate_input(data):       # private: leading underscore
```

### Type Hints

All function signatures require full type annotations. ORM columns use `Mapped[...]`.

```python
async def create_task(
    applicant_id: int,
    title: str,
    task_type: TaskType,
) -> Task:
    ...

class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
```

---

## Architecture Rules

### Layers

Code must respect the layer hierarchy — inner layers must not import from outer layers:

```
Entities (models)
  ↑ imported by
Use Cases (services)
  ↑ imported by
Interface Adapters (handlers, repositories, routes)
  ↑ imported by
External (bot_runner, main)
```

### Adding a New Bot Handler

1. Determine which `StatesGroup` it belongs to (`ApplicantStates`, `ExecutorStates`, `AdminStates`)
2. Add the new state to `app/bot/states/states.py`
3. If the state involves free-text user input, add it to `FLOW_STATES`
4. Implement the handler in the appropriate file under `app/bot/handlers/`
5. Guard admin handlers with `await _assert_admin(user_service, telegram_id)`

```python
# app/bot/handlers/applicant.py
@router.message(ApplicantStates.some_state, F.text == "Button label")
async def handler_name(message: Message, state: FSMContext) -> None:
    ...
```

### Adding Middleware

Register new middleware in `app/bot/bot.py` via `dp.message.middleware(...)`. Middleware must handle the case where `event` is not a `Message`.

### Adding a Service Method

```python
# app/services/task_service.py
async def new_method(self, task_id: int) -> Task:
    task = await self.get_task(task_id)
    task = await self.task_repository.update(task, ...)
    await self.task_repository.commit()
    await self._notion_update(task)  # always call after commit if state changed
    return task
```

### Adding an API Endpoint

```python
# app/api/routes.py
@router.post("/resource", response_model=ResponseSchema, status_code=201)
async def create_resource(
    data: RequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> ResponseSchema:
    ...
```

### Adding Notion Properties

When adding a new field to the Notion property payload, update `_build_full_properties()` in `app/services/notion_sync_service.py`.

---

## Database Schema Changes

```bash
# 1. Update the ORM model in app/database/models/
# 2. Generate migration
alembic revision --autogenerate -m "add_field_to_tasks"

# 3. Review the generated file in migrations/versions/
# 4. Apply
alembic upgrade head
```

---

## Adding Features

### New Executor Specialization

1. Add value to `ExecutorType` enum in `app/database/models/user.py`
2. Add mapping in `_EXECUTOR_TYPE_TO_TASK_TYPE` in `app/bot/handlers/executor.py`
3. Update `get_executor_for_type` in `UserService`
4. Add corresponding `TaskType` value if needed
5. Generate and apply migration

---

## Testing

### Test Structure

```
tests/
├── unit/
│   ├── services/
│   ├── repositories/
│   └── models/
├── integration/
└── conftest.py
```

### Writing Tests

```python
import pytest
from app.services import UserService

@pytest.mark.asyncio
async def test_create_user(user_repository):
    service = UserService(user_repository)
    user = await service.create_user(
        telegram_id=123,
        full_name="Test User",
    )
    assert user.telegram_id == 123
```

---

## Security Best Practices

1. Never commit `.env` files
2. Use environment variables for all secrets
3. Validate all external input at system boundaries (API schemas, bot message text)
4. Use parameterized queries — SQLAlchemy ORM handles this
5. All admin bot operations must call `_assert_admin()` before proceeding
6. Keep CORS restrictions in production; add rate limiting on API endpoints

---

## Pull Request Review Checklist

- [ ] Code follows style guide
- [ ] Full type hints present
- [ ] Docstrings updated where needed
- [ ] `FLOW_STATES` updated if new multi-step state added
- [ ] Notion sync called after every commit that changes task state
- [ ] Admin handlers guarded with `_assert_admin()`
- [ ] No console `print` statements — use `get_logger(__name__)`
- [ ] Documentation updated if behaviour changed
- [ ] All tests pass

---

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with release notes
3. Create release branch: `release/v1.0.0`
4. Merge to `main` via PR
5. Tag: `git tag v1.0.0`
6. Create GitHub release with notes
