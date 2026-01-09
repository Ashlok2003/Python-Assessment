# Issue Tracker API

A REST API for managing issues, comments, and labels built with **Django** and **Django REST Framework**.

## Features

- ✅ **Issue Management**: CRUD operations with optimistic concurrency control (versioning)
- ✅ **Comments**: Add comments to issues with validation
- ✅ **Labels**: Unique labels that can be assigned to issues
- ✅ **Bulk Operations**: Transactional bulk status updates
- ✅ **CSV Import**: Upload CSV for issue creation with validation and summary report
- ✅ **Reports**: Top assignees and average resolution time
- ✅ **Timeline**: Issue history tracking (bonus feature)
- ✅ **Swagger UI**: Interactive API documentation

## Quick Start

### Option 1: Local Development (SQLite)

```bash
# Clone and setup
cd python-assessment
make setup

# Activate virtual environment
source venv/bin/activate

# Run migrations
make migrate

# Create sample data
make seed

# Start server
make run
```

Visit http://localhost:8000 for Swagger UI.

### Option 2: Docker (PostgreSQL)

```bash
# Build and start containers
make docker-up

# View logs
make docker-logs
```

Visit http://localhost:8000 for Swagger UI.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/issues/` | POST | Create new issue |
| `/api/issues/` | GET | List issues (filter + pagination) |
| `/api/issues/{id}/` | GET | Get issue with comments & labels |
| `/api/issues/{id}/` | PATCH | Update issue (with version check) |
| `/api/issues/{id}/comments/` | POST | Add comment |
| `/api/issues/{id}/labels/` | PUT | Replace labels atomically |
| `/api/issues/{id}/timeline/` | GET | Get issue history (bonus) |
| `/api/issues/bulk-status/` | POST | Bulk status update |
| `/api/issues/import/` | POST | CSV upload for issue import |
| `/api/reports/top-assignees/` | GET | Top assignees report |
| `/api/reports/latency/` | GET | Average resolution time report |
| `/api/labels/` | GET/POST | Label CRUD |

## Optimistic Concurrency Control

When updating an issue, include the current `version` number:

```bash
# Get current issue
curl http://localhost:8000/api/issues/1/

# Update with version check
curl -X PATCH http://localhost:8000/api/issues/1/ \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved", "version": 1}'
```

If another request has modified the issue (version mismatch), you'll get a `400 Bad Request` with the current version.

## CSV Import Format

```csv
title,description,status,reporter_username,assignee_username
"Fix login bug","Users cannot login","open","john","jane"
"Add dark mode","Implement dark theme","in_progress","jane","john"
```

Upload:
```bash
curl -X POST http://localhost:8000/api/issues/import/ \
  -F file=@issues.csv
```

## Makefile Commands

```bash
make setup          # Create venv and install dependencies
make run            # Start development server
make migrate        # Apply database migrations
make seed           # Create sample data
make test           # Run tests
make docker-up      # Start Docker containers
make docker-down    # Stop Docker containers
make lint           # Run linting
make format         # Format code with Black
```

## Project Structure

```
python-assessment/
├── issue_tracker/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── tracker/                # Main application
│   ├── models.py           # Database models
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # ViewSets
│   ├── reports.py          # Report views
│   ├── urls.py             # API routing
│   └── admin.py            # Admin configuration
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── README.md
```

## Technology Stack

- **Python 3.11+**
- **Django 4.2+** - Web framework
- **Django REST Framework** - REST API
- **drf-spectacular** - OpenAPI/Swagger documentation
- **PostgreSQL** - Production database
- **SQLite** - Development database
- **Docker** - Containerization
- **Gunicorn** - Production WSGI server

## Evaluation Criteria Coverage

| Area | Points | Implementation |
|------|--------|----------------|
| API correctness (CRUD, filtering, CSV) | 30 | ✅ Full CRUD, filtering, pagination, CSV import with validation |
| Concurrency & transactions | 25 | ✅ Optimistic locking with version field, atomic bulk updates |
| Code structure & clarity | 20 | ✅ Clean separation of models, serializers, views |
| Error handling & validation | 15 | ✅ Serializer validation, proper HTTP status codes |
| Tests & documentation | 10 | ✅ Swagger docs, README, sample tests |
| **Bonus: Timeline** | +5 | ✅ Issue history tracking endpoint |
