.PHONY: help setup install run migrate makemigrations shell test lint format clean docker-up docker-down docker-build docker-logs seed

# Default target
help:
	@echo "Issue Tracker API - Available Commands"
	@echo "======================================="
	@echo ""
	@echo "Development:"
	@echo "  make setup          - Create venv and install dependencies"
	@echo "  make install        - Install dependencies in existing venv"
	@echo "  make run            - Start development server"
	@echo "  make shell          - Open Django shell"
	@echo "  make test           - Run test suite"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Apply database migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make seed           - Create sample data for testing"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start containers"
	@echo "  make docker-down    - Stop containers"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make docker-logs    - View container logs"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linting (flake8)"
	@echo "  make format         - Format code (black)"
	@echo "  make clean          - Clean up cache files"

# Python virtual environment
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
MANAGE := $(PYTHON) manage.py

# Setup virtual environment and install dependencies
setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo ""
	@echo "Setup complete! Run 'source venv/bin/activate' to activate the virtual environment."

# Install dependencies
install:
	$(PIP) install -r requirements.txt

# Run development server
run:
	$(MANAGE) runserver

# Database migrations
migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

# Django shell
shell:
	$(MANAGE) shell

# Run tests
test:
	$(PYTHON) -m pytest -v

# Linting
lint:
	$(VENV)/bin/flake8 tracker/ --max-line-length=120

# Format code
format:
	$(VENV)/bin/black tracker/

# Clean up
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

# Create sample data for testing
seed:
	$(MANAGE) shell -c "\
from django.contrib.auth.models import User; \
from tracker.models import Label, Issue; \
\
# Create users \
admin, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com', 'is_superuser': True, 'is_staff': True}); \
admin.set_password('admin'); \
admin.save(); \
\
user1, _ = User.objects.get_or_create(username='john', defaults={'email': 'john@example.com'}); \
user2, _ = User.objects.get_or_create(username='jane', defaults={'email': 'jane@example.com'}); \
user3, _ = User.objects.get_or_create(username='bob', defaults={'email': 'bob@example.com'}); \
\
# Create labels \
Label.objects.get_or_create(name='bug'); \
Label.objects.get_or_create(name='feature'); \
Label.objects.get_or_create(name='enhancement'); \
Label.objects.get_or_create(name='documentation'); \
Label.objects.get_or_create(name='critical'); \
\
# Create sample issues \
Issue.objects.get_or_create(title='Fix login bug', defaults={'description': 'Users cannot login', 'reporter': user1, 'assignee': user2, 'status': 'open'}); \
Issue.objects.get_or_create(title='Add dark mode', defaults={'description': 'Implement dark theme', 'reporter': user2, 'assignee': user1, 'status': 'in_progress'}); \
Issue.objects.get_or_create(title='Update API docs', defaults={'description': 'Add missing endpoints', 'reporter': user3, 'status': 'open'}); \
\
print('Sample data created successfully!'); \
"
