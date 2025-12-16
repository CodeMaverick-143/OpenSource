.PHONY: help install install-dev lint format test run docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make lint         - Run linting checks (ruff, black, isort)"
	@echo "  make format       - Auto-format code with black and isort"
	@echo "  make test         - Run tests with pytest"
	@echo "  make run          - Run the FastAPI application locally"
	@echo "  make docker-up    - Start all services with Docker Compose"
	@echo "  make docker-down  - Stop all Docker services"
	@echo "  make clean        - Remove cache and build artifacts"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

lint:
	@echo "Running ruff..."
	ruff check backend/ tests/
	@echo "Checking black formatting..."
	black --check --line-length=100 backend/ tests/
	@echo "Checking isort..."
	isort --check-only --profile=black --line-length=100 backend/ tests/

format:
	@echo "Formatting with black..."
	black --line-length=100 backend/ tests/
	@echo "Sorting imports with isort..."
	isort --profile=black --line-length=100 backend/ tests/
	@echo "Auto-fixing with ruff..."
	ruff check --fix backend/ tests/

test:
	pytest tests/ -v --cov=backend --cov-report=term-missing

run:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
