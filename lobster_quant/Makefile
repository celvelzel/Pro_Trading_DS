# Lobster Quant - Makefile
# Common development commands

.PHONY: help install test lint format clean run

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Setup
# ============================================================

install: ## Install dependencies
	pip install -e ".[dev]"

install-prod: ## Install production dependencies only
	pip install -e .

# ============================================================
# Testing
# ============================================================

test: ## Run all tests
	python -m pytest tests/ -v

test-unit: ## Run unit tests only
	python -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	python -m pytest tests/integration/ -v

test-fast: ## Run tests without verbose output
	python -m pytest tests/ -q

test-cov: ## Run tests with coverage report
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

test-slow: ## Run slow tests only
	python -m pytest tests/ -m slow -v

# ============================================================
# Code Quality
# ============================================================

lint: ## Run linter (ruff)
	python -m ruff check src/ tests/

lint-fix: ## Auto-fix linting issues
	python -m ruff check --fix src/ tests/

format: ## Format code with black
	python -m black src/ tests/

format-check: ## Check formatting without changing files
	python -m black --check src/ tests/

typecheck: ## Run type checker (mypy)
	python -m mypy src/

check: ## Run all quality checks
	@echo "=== Linting ==="
	python -m ruff check src/ tests/
	@echo "=== Formatting ==="
	python -m black --check src/ tests/
	@echo "=== Type checking ==="
	python -m mypy src/

fix: ## Auto-fix all issues
	python -m ruff check --fix src/ tests/
	python -m black src/ tests/

# ============================================================
# Running
# ============================================================

run: ## Run the Streamlit app (legacy v1 entry)
	streamlit run app.py

run-v2: ## Run the new v2 Streamlit app
	streamlit run app_v2.py

run-debug: ## Run in debug mode
	DEBUG=true streamlit run app_v2.py

# ============================================================
# Cleanup
# ============================================================

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf data/cache/*.pkl data/cache/*.json
	rm -rf logs/

clean-all: clean ## Clean everything including test cache
	rm -rf test_cache/
	rm -rf .mypy_cache/

# ============================================================
# Development
# ============================================================

cache-stats: ## Show cache statistics
	python -c "from src.data.cache import DataCache; c = DataCache(); print(c.get_stats())"

cache-clear: ## Clear data cache
	python -c "from src.data.cache import DataCache; c = DataCache(); print(f'Cleared {c.clear()} items')"

providers: ## List available data providers
	python -c "from src.data.providers import DataProviderFactory; print(DataProviderFactory.get_available())"

indicators: ## List available indicators
	python -c "from src.analysis.indicators import IndicatorRegistry; print(IndicatorRegistry.list_indicators())"
