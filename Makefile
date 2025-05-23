# Retroclamp Development Makefile

.PHONY: help install dev-install test lint format clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

dev-install:  ## Install development dependencies
	pip install -r requirements.txt
	pip install pre-commit pytest pytest-cov black isort flake8 bandit safety mypy
	pre-commit install

test:  ## Run tests
	pytest --cov=. --cov-report=term --cov-report=html

lint:  ## Run linting
	pre-commit run --all-files

format:  ## Format code
	black .
	isort .

security:  ## Run security checks
	bandit -r .
	safety check

analyze:  ## Run code analysis (if available)
	@if [ -f "retroclamp_analyzer.py" ]; then python retroclamp_analyzer.py .; fi

clean:  ## Clean generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/

run:  ## Run the application
	python main.py
