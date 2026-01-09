# Issue Tracker API 🎫

Hey there! This is a REST API for managing issues, comments, and labels - think of it like a simplified Jira or GitHub Issues. Built with Django and Django REST Framework.

## What's Inside?

This project covers most of what you'd need in a real issue tracker:
- **Issues** with full CRUD, plus optimistic locking so two people don't overwrite each other's changes
- **Comments** on issues (can't be empty, obviously)
- **Labels** that you can attach to issues
- **Bulk updates** - change status of multiple issues at once, all-or-nothing
- **CSV import** - upload a spreadsheet of issues
- **Reports** - who's got the most issues assigned, how fast are we resolving stuff
- **Timeline** - see the history of changes on an issue (bonus feature!)

## Architecture Overview

Here's how the pieces fit together:

```mermaid
flowchart TB
    subgraph Client
        Browser[Browser / Swagger UI]
        CLI[curl / httpie]
    end

    subgraph Django["Django Application"]
        URLs[URL Router]
        Views[ViewSets & Views]
        Serial[Serializers]
        Models[Models / ORM]
    end

    subgraph External
        DB[(PostgreSQL / SQLite)]
        Swagger[OpenAPI Schema]
    end

    Browser --> |HTTP Request| URLs
    CLI --> |HTTP Request| URLs
    URLs --> Views
    Views --> Serial
    Serial --> |Validate & Transform| Views
    Views --> Models
    Models --> |SQL| DB
    Views --> |JSON Response| Browser
    URLs --> Swagger
    Swagger --> |/api/docs/| Browser
```

## Database Design

Four main tables with a junction table for the many-to-many relationship:

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string email
    }

    ISSUE {
        int id PK
        string title
        text description
        enum status
        int version
        int reporter_id FK
        int assignee_id FK
        datetime created_at
        datetime resolved_at
    }

    COMMENT {
        int id PK
        text body
        int issue_id FK
        int author_id FK
        datetime created_at
    }

    LABEL {
        int id PK
        string name UK
        datetime created_at
    }

    ISSUE_HISTORY {
        int id PK
        int issue_id FK
        enum change_type
        text old_value
        text new_value
        datetime timestamp
    }

    USER ||--o{ ISSUE : "reports"
    USER ||--o{ ISSUE : "assigned to"
    USER ||--o{ COMMENT : "writes"
    ISSUE ||--o{ COMMENT : "has"
    ISSUE }o--o{ LABEL : "tagged with"
    ISSUE ||--o{ ISSUE_HISTORY : "tracks"
```

**Why the `version` field?** It's for optimistic concurrency control. When you update an issue, you send the version you have. If someone else updated it first, the versions won't match and you'll get an error. No accidental overwrites.

## Getting Started

### Quick Start (SQLite, no Docker needed)

```bash
# Set up the project
make setup
source venv/bin/activate

# Create tables and add some test data
make migrate
make seed

# Fire it up
make run
```

Now open http://localhost:8000 - you'll see the Swagger UI where you can try out every endpoint.

### With Docker (PostgreSQL)

```bash
make docker-up
```

Same deal, just go to http://localhost:8000.

## API Endpoints

| Endpoint | What it does |
|----------|--------------|
| `GET /api/issues/` | List all issues (has filtering & pagination) |
| `POST /api/issues/` | Create a new issue |
| `GET /api/issues/{id}/` | Get one issue with its comments and labels |
| `PATCH /api/issues/{id}/` | Update an issue (include `version`!) |
| `POST /api/issues/{id}/comments/` | Add a comment |
| `PUT /api/issues/{id}/labels/` | Replace all labels on an issue |
| `GET /api/issues/{id}/timeline/` | See change history |
| `POST /api/issues/bulk-status/` | Update multiple issues at once |
| `POST /api/issues/import/` | Upload CSV to create issues |
| `GET /api/reports/top-assignees/` | Who has the most issues? |
| `GET /api/reports/latency/` | How fast are issues being resolved? |

## How Optimistic Locking Works

Here's the flow:

```mermaid
sequenceDiagram
    participant C1 as Client A
    participant C2 as Client B
    participant API as Issue Tracker API
    participant DB as Database

    C1->>API: GET /issues/1/
    API->>DB: SELECT * FROM issues WHERE id=1
    DB-->>API: {id: 1, title: "Bug", version: 1}
    API-->>C1: {id: 1, title: "Bug", version: 1}

    C2->>API: GET /issues/1/
    API-->>C2: {id: 1, title: "Bug", version: 1}

    C1->>API: PATCH /issues/1/ {title: "Fixed Bug", version: 1}
    API->>DB: UPDATE issues SET title="Fixed Bug", version=2 WHERE id=1 AND version=1
    DB-->>API: 1 row updated
    API-->>C1: 200 OK {version: 2}

    C2->>API: PATCH /issues/1/ {title: "Critical Bug", version: 1}
    API->>DB: Check version
    Note over API: Version mismatch! Expected 1, current is 2
    API-->>C2: 400 Bad Request "Version conflict. Current version is 2."
```

## CSV Import Format

Your CSV should look like this:

```csv
title,description,status,reporter_username,assignee_username
"Login page broken","Users can't log in","open","john","jane"
"Add dark mode","Would be nice to have","in_progress","jane","bob"
```

Upload it and you'll get back a report:
```json
{
  "total_rows": 2,
  "successful": 2,
  "failed": 0,
  "errors": []
}
```

## Project Structure

```
├── issue_tracker/          # Django project config
│   ├── settings.py         # All the settings
│   └── urls.py             # Root URL routing + Swagger
├── tracker/                # The actual app
│   ├── models.py           # Issue, Comment, Label, IssueHistory
│   ├── serializers.py      # Request/response validation
│   ├── views.py            # All the endpoint logic
│   ├── reports.py          # Report endpoints
│   └── admin.py            # Django admin setup
├── tests/                  # Pytest tests
├── Dockerfile              # For containerization
├── docker-compose.yml      # PostgreSQL + app
└── Makefile                # Handy shortcuts
```

## Useful Commands

```bash
make run            # Start the dev server
make test           # Run the test suite
make docker-up      # Spin up with Docker
make docker-down    # Tear it down
make seed           # Create sample data
make shell          # Django shell for debugging
```

## Tech Stack

- **Django 4.2+** - Web framework
- **Django REST Framework** - API toolkit
- **drf-spectacular** - Auto-generated Swagger docs
- **PostgreSQL** - Production database
- **SQLite** - Development (zero config)
- **Docker** - Containerization

---

Built as a backend assessment project. Feel free to poke around!
