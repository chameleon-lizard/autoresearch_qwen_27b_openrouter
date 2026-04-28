.PHONY: help test lint format install clean

help: ## Show this help message
	@echo "Available commands:"
	@echo "  make help     - Show this help message"
	@echo "  make install  - Install dependencies"
	@echo "  make test     - Run all tests"
	@echo "  make lint     - Run linter (ruff)"
	@echo "  make format   - Format code (ruff)"
	@echo "  make check    - Run lint and tests"
	@echo "  make clean    - Remove build artifacts"

install: ## Install dependencies
	pip install -r requirements.txt
	pip install -e ".[dev]"

test: ## Run all tests
	pytest autoresearch/tests/ -v

lint: ## Run linter
	ruff check autoresearch/

format: ## Format code
	ruff check --fix autoresearch/

check: lint test ## Run lint and tests

clean: ## Remove build artifacts
	rm -rf __pycache__
	rm -rf autoresearch/__pycache__
	rm -rf autoresearch/tests/__pycache__
	rm -rf .pytest_cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
