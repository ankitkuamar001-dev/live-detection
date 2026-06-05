.PHONY: help install run test lint format type-check docker-build docker-up docker-down \
       db-migrate db-revision clean download-weights

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
PYTHON     ?= python3
APP_MODULE ?= src.main:app
ALEMBIC    ?= alembic

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
install: ## Install the package in editable mode with dev dependencies
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e '.[dev]'

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
run: ## Start the development server with hot-reload
	uvicorn $(APP_MODULE) --reload --host 0.0.0.0 --port 8000

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
test: ## Run the test suite with coverage
	pytest

lint: ## Lint source and test files
	ruff check src/ tests/

format: ## Auto-format source and test files
	ruff format src/ tests/

type-check: ## Run mypy strict type checking
	mypy src/

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all services in detached mode
	docker compose up -d

docker-down: ## Stop and remove all services
	docker compose down -v

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
db-migrate: ## Apply all pending Alembic migrations
	$(ALEMBIC) upgrade head

db-revision: ## Auto-generate a new Alembic migration
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
download-weights: ## Download pre-trained model weights
	bash scripts/download_weights.sh

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove build artifacts, caches, and temporary files
	rm -rf build/ dist/ *.egg-info .mypy_cache .ruff_cache .pytest_cache
	rm -rf reports/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."
