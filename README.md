# ContriVerse - Open Source Contribution Platform

> A production-ready platform that tracks GitHub PR contributions, reviews them, and ranks contributors fairly.

[![CI](https://github.com/yourusername/contriverse/workflows/CI/badge.svg)](https://github.com/yourusername/contriverse/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🎯 Project Overview

ContriVerse is an open-source contribution tracking platform built with FastAPI, PostgreSQL, Redis, and Celery. It provides a complete infrastructure for tracking GitHub contributions, managing projects, and building contributor leaderboards.

## 🏗️ Architecture

```
backend/
├── core/           # Core configuration, logging, middleware
├── api/            # API endpoints (versioned)
├── db/             # Database models and session management
├── worker/         # Celery background tasks
└── main.py         # FastAPI application entry point

alembic/            # Database migrations
tests/              # Test suite
```

### Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Background Jobs**: Celery
- **Logging**: Structlog (JSON)
- **Migrations**: Alembic
- **Testing**: Pytest + pytest-asyncio

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd OpenSource
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env and set SECRET_KEY (generate with: openssl rand -hex 32)
   ```

3. **Start services with Docker**
   ```bash
   make docker-up
   ```

4. **Access the application**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health

### Manual Setup (Without Docker)

1. **Create virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   make install-dev
   ```

3. **Start PostgreSQL and Redis**
   ```bash
   # Using Docker for services only
   docker-compose up -d postgres redis
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the application**
   ```bash
   make run
   ```

6. **Start Celery worker (in another terminal)**
   ```bash
   celery -A backend.worker.celery_app worker --loglevel=info
   ```

## 🛠️ Development

### Available Commands

```bash
make help           # Show all available commands
make install        # Install production dependencies
make install-dev    # Install development dependencies + pre-commit hooks
make lint           # Run linting checks (ruff, black, isort)
make format         # Auto-format code
make test           # Run tests with coverage
make run            # Run FastAPI application
make docker-up      # Start all services with Docker
make docker-down    # Stop all Docker services
make clean          # Remove cache and build artifacts
```

### Code Quality

This project enforces strict code quality standards:

- **Black**: Code formatting (line length: 100)
- **isort**: Import sorting
- **Ruff**: Fast Python linter
- **Pre-commit hooks**: Auto-format on commit

Install pre-commit hooks:
```bash
pre-commit install
```

Run pre-commit manually:
```bash
pre-commit run --all-files
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_health.py -v

# Run with specific markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
```

## 📝 Environment Configuration

The application uses Pydantic Settings for configuration management. Three environments are supported:

- **development**: Debug mode, console logging
- **testing**: Test database, minimal logging
- **production**: JSON logging, strict validation

### Required Environment Variables

```bash
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db_name

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (REQUIRED)
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

See `.env.example` for complete configuration options.

## 🗄️ Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "description of changes"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## 🔍 Logging

The application uses **structlog** for structured JSON logging with the following features:

- Request ID tracking
- User ID context (when available)
- Environment-specific formatting (JSON for production, console for development)
- Automatic log correlation across API and Celery workers

Example log output (JSON):
```json
{
  "event": "request_completed",
  "request_id": "abc-123",
  "method": "GET",
  "path": "/api/v1/health",
  "status_code": 200,
  "duration_ms": 12.34,
  "timestamp": "2025-12-16T18:30:00Z"
}
```

## 🐳 Docker

### Services

- **postgres**: PostgreSQL 16 with health checks
- **redis**: Redis 7 with persistence
- **backend**: FastAPI application
- **celery_worker**: Background job processor

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f celery_worker

# Stop services
docker-compose down

# Rebuild services
docker-compose up -d --build
```

## 🧪 Testing Strategy

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test API endpoints with database
- **Coverage target**: 80%+

## 📚 API Documentation

When running in development mode, interactive API documentation is available:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Security

- Environment-based configuration
- Secret key validation (fails if not set properly)
- CORS configuration
- Request ID tracking
- Structured audit logging

## 🚦 CI/CD

GitHub Actions workflow runs on every PR and push to main:

1. Setup Python 3.12
2. Install dependencies
3. Run linting (ruff, black, isort)
4. Run tests with coverage
5. Fail if coverage < 80%

## 📖 Project Structure Explained

### Why These Tools?

- **FastAPI**: Modern, fast, with automatic API docs and type checking
- **SQLAlchemy 2.0**: Async support, type-safe ORM
- **Structlog**: Production-grade structured logging
- **Celery**: Reliable background job processing
- **Alembic**: Database migration management
- **Ruff**: 10-100x faster than flake8/pylint
- **Black**: Uncompromising code formatter
- **Pydantic Settings**: Type-safe configuration with validation

### Design Decisions

1. **Async/await throughout**: Better performance for I/O-bound operations
2. **Structured logging**: Essential for production debugging and monitoring
3. **Environment-specific configs**: Clean separation of dev/test/prod
4. **Docker Compose**: Consistent development environment
5. **Pre-commit hooks**: Catch issues before they reach CI

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `make lint && make test`
5. Commit your changes (pre-commit hooks will run)
6. Push and create a Pull Request

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🔗 Related Documentation

- [PRD.md](PRD.md) - Product Requirements Document
- [todo.md](todo.md) - Development Roadmap
pensource contributor
