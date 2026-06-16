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
source venv/Scripts/activate  # Windows: venv\Scripts\activate
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

## Development Workflow

### Before Making Changes

1. Create feature branch: `git checkout -b feature/description`
2. Keep branch updated with main
3. Write tests for new features

### Making Changes

1. Follow PEP 8 style guide
2. Add type hints to all functions
3. Write docstrings for modules, classes, and functions
4. Update relevant documentation

### Code Quality

#### Format Code

```bash
bash format.sh
```

#### Run Checks

```bash
bash check.sh
```

#### Type Checking

```bash
mypy app/
```

#### Linting

```bash
flake8 app/
```

#### Testing

```bash
pytest
pytest --cov=app  # With coverage
```

### Commit Guidelines

- Write clear commit messages
- Reference issues: `Fixes #123`
- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`

Example:

```
feat: add task escalation workflow

- Implement escalation logic
- Add escalation status
- Update documentation

Fixes #456
```

### Creating Pull Requests

1. Push branch: `git push origin feature/description`
2. Create PR with clear description
3. Link related issues
4. Ensure CI passes
5. Request review from team members

## Code Style

### Naming Conventions

```python
# Constants
EXECUTOR_TIMEOUT = 3600

# Functions and methods
def get_user_by_telegram_id(telegram_id: int) -> User | None:
    pass

# Classes
class UserService:
    pass

# Private methods
def _validate_input(data: dict) -> None:
    pass
```

### Type Hints

```python
# Function signatures
async def create_task(
    applicant_id: int,
    title: str,
    task_type: TaskType,
) -> Task:
    pass

# Class attributes
class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
```

### Docstrings

```python
def classify_ticket(self, description: str) -> AIClassificationResponse:
    """Classify a ticket using AI.

    Args:
        description: Natural language ticket description

    Returns:
        Classification response with type, priority, and executor

    Raises:
        AIServiceError: If classification fails
    """
    pass
```

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
    """Test user creation."""
    service = UserService(user_repository)
    user = await service.create_user(
        telegram_id=123,
        full_name="Test User"
    )
    assert user.telegram_id == 123
    assert user.full_name == "Test User"
```

## Adding Features

### 1. Database Schema Changes

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Review migration in migrations/versions/

# Apply migration
alembic upgrade head
```

### 2. Add Model Fields

```python
# In database/models/task.py
class Task(Base):
    # ... existing fields ...
    new_field: Mapped[str] = mapped_column(String(255), nullable=True)
```

### 3. Add Service Methods

```python
# In services/task_service.py
async def new_method(self, param: Type) -> ReturnType:
    """Method docstring."""
    # Implementation
    pass
```

### 4. Add API Endpoint

```python
# In api/routes.py
@router.post("/endpoint", response_model=ResponseSchema)
async def endpoint(
    request: RequestSchema,
    session: AsyncSession = Depends(get_db_session),
) -> ResponseSchema:
    """Endpoint docstring."""
    pass
```

### 5. Add Bot Handler

```python
# In bot/handlers/applicant.py
@router.message(ApplicantStates.state, F.text == "trigger")
async def handler_name(message: Message, state: FSMContext) -> None:
    """Handler docstring."""
    pass
```

## Documentation

### Updating Documentation

1. Update relevant markdown files (README, SETUP, ARCHITECTURE, etc.)
2. Add inline code comments for complex logic
3. Update API docs if endpoints change
4. Add examples for new features

### Documentation Standards

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Keep documentation DRY

## Performance Optimization

### Common Optimization Areas

1. **Database Queries**
   - Use indexes on frequently queried columns
   - Use eager loading for relationships
   - Avoid N+1 queries

2. **API Responses**
   - Paginate list endpoints
   - Use projection to reduce data
   - Enable compression

3. **Bot Performance**
   - Use async operations
   - Implement caching for AI responses
   - Optimize state management

## Security Best Practices

1. Never commit `.env` files
2. Use environment variables for secrets
3. Validate all user inputs
4. Use parameterized queries (ORM handles this)
5. Add CORS restrictions
6. Implement rate limiting for APIs
7. Use strong password requirements
8. Enable HTTPS in production

## Bug Reports

### Include in Bug Report

- Clear description of issue
- Steps to reproduce
- Expected vs actual behavior
- Screenshots/logs if applicable
- Environment details (OS, Python version, etc.)

Example:

```
Title: Bot not responding to /start command

Description:
Bot doesn't respond when user sends /start

Steps to Reproduce:
1. Start bot with `python app/bot_runner.py`
2. Open Telegram
3. Send /start to bot

Expected:
Bot shows welcome menu

Actual:
Bot shows no response

Environment:
- Windows 10
- Python 3.13
- PostgreSQL 16
```

## Pull Request Review Checklist

Before requesting review, ensure:

- [ ] Code follows style guide
- [ ] All tests pass
- [ ] Type hints present
- [ ] Docstrings added
- [ ] Documentation updated
- [ ] No console errors
- [ ] No debug code left in
- [ ] Commit messages clear

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG
3. Create release branch: `release/v1.0.0`
4. Merge to main with PR
5. Tag release: `git tag v1.0.0`
6. Create GitHub release with notes

## Questions?

- Check existing documentation
- Review similar code
- Ask in discussions
- Create issue for clarification

Thank you for contributing!
