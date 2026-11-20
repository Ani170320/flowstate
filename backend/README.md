# FLOWSTATE – Backend API (FastAPI)

Scalable, asynchronous backend foundation for **FLOWSTATE**, a project management and team collaboration SaaS platform.

Built with Python 3.12+, FastAPI, SQLAlchemy 2.0, PostgreSQL (Supabase), Alembic, and Pydantic v2.

---

## Architecture & Technology Stack

| Layer | Technology | Description |
|---|---|---|
| **Runtime & Language** | Python 3.12+ | Asynchronous event loop with native type hinting |
| **Framework** | FastAPI | High-performance ASGI web framework |
| **ASGI Server** | Uvicorn | Lightning-fast ASGI HTTP server |
| **Database** | PostgreSQL / Supabase | Cloud PostgreSQL with pooled connection support |
| **ORM** | SQLAlchemy 2.0 | Asynchronous declarative ORM |
| **Async Driver** | asyncpg / psycopg | High-concurrency PostgreSQL drivers |
| **Migrations** | Alembic | Asynchronous schema migration framework |
| **Configuration** | Pydantic Settings | 12-factor environment configuration |
| **Validation** | Pydantic v2 | Strict schema validation and serialization |
| **Testing** | pytest & pytest-asyncio | Asynchronous test suite with HTTPX |

---

## Project Structure

```text
backend/
│
├── app/
│   ├── main.py                 # FastAPI application initialization & lifecycle
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings & environment variables
│   │   └── exceptions.py       # Centralized exception handlers & error models
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   └── health.py           # /api/v1/health & /api/v1/health/ready
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py       # SQLAlchemy 2.0 async engine & session management
│   │
│   ├── models/
│   │   └── __init__.py         # Declarative Base & future ORM models
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── health.py           # Pydantic v2 request/response schemas
│   │
│   ├── services/
│   │   └── __init__.py         # Business logic layer (future modules)
│   │
│   └── dependencies/
│       ├── __init__.py
│       └── database.py         # FastAPI dependency injection (get_db)
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures & async test client
│   └── test_health.py          # Liveness, readiness, CORS & exception tests
│
├── alembic/                    # Database migration environment
│   ├── env.py                  # Async migration runner
│   ├── script.py.mako          # Revision template
│   └── versions/               # Generated migration scripts
│
├── alembic.ini                 # Alembic configuration file
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Project dependencies
├── .env.example                # Example environment configuration
├── .gitignore                  # Git ignore rules for backend
└── README.md                   # Backend documentation
```

---

## Getting Started

### 1. Prerequisites

- Python 3.12+ (or 3.13+)
- Git
- Supabase account (for PostgreSQL database when ready)

### 2. Environment Setup

Create and activate a virtual environment:

```bash
cd backend

# On Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# On macOS/Linux:
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Configure your environment variables in `.env`:

```env
APP_NAME=FLOWSTATE
APP_ENV=development
APP_DEBUG=true

# Supabase PostgreSQL Shared Pooler Connection:
# Percent-encode special characters in your password (e.g. '@' -> '%40', '#' -> '%23')
DATABASE_URL=postgresql://postgres.bpcubzxhphdvzhxanpse:[YOUR-PASSWORD]@aws-1-ap-south-1.pooler.supabase.com:5432/postgres

FRONTEND_URL=http://localhost:3000
SECRET_KEY=generate-a-strong-random-key-here
```

> **Note:** The backend server starts cleanly even if `DATABASE_URL` is empty. The basic health-check foundation does not require an active database connection to run.

---

## Running the Development Server

Start the FastAPI application with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, the following endpoints are available:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

---

## Health Check API Endpoints

### 1. Liveness Probe: `GET /api/v1/health`

Confirms the application process is alive and responsive.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "application": "FLOWSTATE",
  "version": "1.0.0"
}
```

### 2. Readiness Probe: `GET /api/v1/health/ready`

Checks whether downstream dependencies (database connection) are ready to accept traffic. If `DATABASE_URL` is not yet configured, it reports the status accurately without pretending to be connected.

**Response when database is unconfigured (200 OK):**
```json
{
  "status": "not_ready",
  "database": "unconfigured",
  "details": "Database URL is not configured. Backend foundation is operational."
}
```

**Response when database is connected (200 OK):**
```json
{
  "status": "ready",
  "database": "connected",
  "details": "Database connection verified successfully."
}
```

---

## Database Preparation & Migrations (Alembic)

The database engine is configured for asynchronous SQLAlchemy 2.0 with `asyncpg`.

When you are ready to configure Supabase:

1. Add your Supabase connection string to `DATABASE_URL` in `backend/.env`.
2. Generate initial schema migration:
   ```bash
   alembic revision --autogenerate -m "initial_schema"
   ```
3. Apply migrations to Supabase:
   ```bash
   alembic upgrade head
   ```

---

## API Modules

### 1. Authentication & Tenant Resolution (`/api/v1/auth`)

- `POST /api/v1/auth/verify`: Verifies incoming Bearer JWT against Supabase Auth (supports ES256 via JWKS and local fallback).
- `GET /api/v1/auth/me`: Resolves the active user profile, primary organization membership, and available workspaces.
- `POST /api/v1/auth/switch-organization`: Switches active tenant context.

### 2. Organization & Workspace Management (`/api/v1/organizations`)

- `POST /api/v1/organizations`: Creates new tenant organization. Enrolls creator as Owner.
  - **Subscription Security**: New organizations strictly default to the `free` plan. Client attempts to pass `pro` or `enterprise` plans are rejected.
- `GET /api/v1/organizations`: Lists all organizations where caller is an enrolled member.
- `GET /api/v1/organizations/{org_id}`: Retrieves organization profile and member counts.
- `PATCH /api/v1/organizations/{org_id}`: Updates name, slug, or logo (Requires Owner or Admin). Plan modifications via standard PATCH are restricted.
- `POST /api/v1/organizations/{org_id}/billing/plan`: Dedicated server-side billing process endpoint for plan upgrades (requires valid `X-Billing-Secret`).
- `GET /api/v1/organizations/{org_id}/members`: Lists enrolled organization members.
- `POST /api/v1/organizations/{org_id}/members`: Enrolls user by email or user_id (Requires Owner or Admin).
- `PATCH /api/v1/organizations/{org_id}/members/{user_id}`: Updates member role with hierarchy and sole-owner demotion guards.
- `DELETE /api/v1/organizations/{org_id}/members/{user_id}`: Expels member or allows self-leave.
- `GET /api/v1/organizations/{org_id}/settings`: Retrieves workspace currency, timezone, working days, and notification flags.
- `PATCH /api/v1/organizations/{org_id}/settings`: Updates workspace settings (Requires Owner or Admin).

### 3. Teams API (`/api/v1/teams` & `/api/v1/organizations/{org_id}/teams`)

- `POST /api/v1/organizations/{org_id}/teams`: Creates functional team unit (Requires Manager, Admin, or Owner).
- `GET /api/v1/organizations/{org_id}/teams`: Lists teams belonging to the organization.
- `GET /api/v1/organizations/{org_id}/teams/{team_id}`: Retrieves team details and enrolled members.
- `PATCH /api/v1/organizations/{org_id}/teams/{team_id}`: Updates team name, description, or lead (Requires Manager, Admin, Owner, or Team Lead).
- `DELETE /api/v1/organizations/{org_id}/teams/{team_id}`: Deletes team (Requires Admin or Owner).
- `GET /api/v1/organizations/{org_id}/teams/{team_id}/members`: Lists team members.
- `POST /api/v1/organizations/{org_id}/teams/{team_id}/members`: Enrolls organization member into team.
- `DELETE /api/v1/organizations/{org_id}/teams/{team_id}/members/{user_id}`: Removes member from team (supports self-leave).

### 4. Projects API (`/api/v1/projects` & `/api/v1/organizations/{org_id}/projects`)

- `POST /api/v1/organizations/{org_id}/projects`: Creates project container with key derivation and unique key validation (Requires Manager, Admin, or Owner).
- `GET /api/v1/organizations/{org_id}/projects`: Lists organization projects with optional `team_id`, `status`, and `priority` query filters.
- `GET /api/v1/organizations/{org_id}/projects/{project_id}`: Retrieves project details and members.
- `PATCH /api/v1/organizations/{org_id}/projects/{project_id}`: Updates project metadata, progress, budget, status (Requires Manager, Admin, Owner, or Project Manager).
- `DELETE /api/v1/organizations/{org_id}/projects/{project_id}`: Deletes project container (Requires Admin or Owner).
- `GET /api/v1/organizations/{org_id}/projects/{project_id}/members`: Lists project member assignments.
- `POST /api/v1/organizations/{org_id}/projects/{project_id}/members`: Assigns organization member to project.
- `DELETE /api/v1/organizations/{org_id}/projects/{project_id}/members/{user_id}`: Removes user from project (supports self-leave).

### 5. Tasks & Kanban API (`/api/v1/tasks`, `/api/v1/projects/{project_id}/tasks`, `/api/v1/projects/{project_id}/kanban`)

- `POST /api/v1/projects/{project_id}/tasks`: Creates a task within a project. Uses atomic project counter locking (`with_for_update()`) to generate human-friendly sequential keys (e.g. `FLW-101`). Enforces assignee organization validation.
- `GET /api/v1/projects/{project_id}/tasks`: Lists tasks in a project with filtering by `status`, `priority`, `assignee_id`, and fuzzy text `search`.
- `GET /api/v1/tasks/{task_id}`: Retrieves comprehensive task details including assignee, creator, subtask completion metrics, and attached labels.
- `PATCH /api/v1/tasks/{task_id}`: Modifies task metadata, dates, estimated/actual hours, or reassigns/unassigns user. Requires Manager, Admin, Owner, Task Creator, or Task Assignee.
- `DELETE /api/v1/tasks/{task_id}`: Deletes task and cascades to subtasks and label associations. Requires Manager, Admin, Owner, or Task Creator.
- `GET /api/v1/projects/{project_id}/kanban`: Returns complete Kanban board partitioned into status columns (`backlog`, `todo`, `in_progress`, `in_review`, `done`), ordered by fractional `order ASC`.
- `PATCH /api/v1/tasks/{task_id}/status`: Dedicated status transition endpoint to move tasks across columns.
- `PATCH /api/v1/tasks/{task_id}/position`: Fractional positioning endpoint computing midpoint order between adjacent tasks (`before_task_id`, `after_task_id`) or repositioning to top/bottom of column.

### 6. Subtasks API (`/api/v1/tasks/{task_id}/subtasks` & `/api/v1/subtasks/{subtask_id}`)

- `POST /api/v1/tasks/{task_id}/subtasks`: Adds a checklist item to a task with display ordering.
- `GET /api/v1/tasks/{task_id}/subtasks`: Lists checklist items sorted by `order ASC`.
- `PATCH /api/v1/subtasks/{subtask_id}`: Updates checklist item title, completion state (`completed: true/false`), or display order.
- `DELETE /api/v1/subtasks/{subtask_id}`: Removes checklist item from task.

### 7. Labels API (`/api/v1/organizations/{org_id}/labels`, `/api/v1/labels/{label_id}`, `/api/v1/tasks/{task_id}/labels/{label_id}`)

- `POST /api/v1/organizations/{org_id}/labels`: Creates organization-scoped taxonomy label with hex color and case-insensitive unique name validation.
- `GET /api/v1/organizations/{org_id}/labels`: Lists all labels defined for an organization.
- `GET /api/v1/labels/{label_id}`: Retrieves label details.
- `PATCH /api/v1/labels/{label_id}`: Updates label name or hex color.
- `DELETE /api/v1/labels/{label_id}`: Deletes label and removes associations.
- `POST /api/v1/tasks/{task_id}/labels/{label_id}`: Attaches an organization label to a task (verifies cross-tenant isolation).
- `DELETE /api/v1/tasks/{task_id}/labels/{label_id}`: Detaches a label from a task.

### 8. Comments API (`/api/v1/tasks/{task_id}/comments` & `/api/v1/comments/{comment_id}`)

- `POST /api/v1/tasks/{task_id}/comments`: Posts discussion comment on a task within the tenant organization. Dispatches in-app notification to task assignee and logs an audit activity event.
- `GET /api/v1/tasks/{task_id}/comments`: Retrieves chronologically sorted, paginated comments with author profiles.
- `PATCH /api/v1/comments/{comment_id}`: Edits comment text. Restricted to original author or organization Manager, Admin, or Owner.
- `DELETE /api/v1/comments/{comment_id}`: Deletes comment. Restricted to original author or organization Manager, Admin, or Owner.

### 9. Attachments API (`/api/v1/tasks/{task_id}/attachments` & `/api/v1/attachments/{attachment_id}`)

- `POST /api/v1/tasks/{task_id}/attachments`: Validates file size and allowed MIME types, uploads binary content to Supabase Storage in organization-scoped paths (`org_{org_id}/tasks/{task_id}/{unique}_{name}`), and stores metadata in PostgreSQL. Automatically rolls back storage objects if database transaction fails.
- `GET /api/v1/tasks/{task_id}/attachments`: Lists file attachments for a task with public/signed download URLs and uploader metadata.
- `DELETE /api/v1/attachments/{attachment_id}`: Deletes metadata record from PostgreSQL and removes binary object from Supabase Storage (preventing orphaned storage objects). Restricted to uploader or Manager, Admin, or Owner.

### 10. Activity Audit Trail API (`/api/v1/organizations/{org_id}/activities`, `/api/v1/projects/{project_id}/activities`, `/api/v1/tasks/{task_id}/activities`)

- `GET /api/v1/organizations/{org_id}/activities`: Lists paginated, append-only organization audit logs ordered by `created_at DESC`.
- `GET /api/v1/projects/{project_id}/activities`: Lists activities scoped to a specific project.
- `GET /api/v1/tasks/{task_id}/activities`: Lists timeline activities scoped to a specific task (creation, assignment, status change, comments, attachments).

### 11. Notifications API (`/api/v1/notifications`)

- `GET /api/v1/notifications`: Retrieves authenticated user's notification inbox with filtering by `unread_only`, category `type`, and pagination.
- `GET /api/v1/notifications/unread-count`: Polling endpoint returning user's active unread badge count.
- `PATCH /api/v1/notifications/{notification_id}/read`: Marks an individual notification as read.
- `PATCH /api/v1/notifications/read-all`: Bulk transitions all unread notifications to read.
- `DELETE /api/v1/notifications/{notification_id}`: Removes notification from user inbox.

### 12. Calendar API (`/api/v1/calendar`, `/api/v1/calendar/events`, `/api/v1/calendar/upcoming`)

- `GET /api/v1/calendar`: Aggregates tasks, milestones, and project deadlines into daily buckets across `month`, `week`, or `day` views. Supports date windowing, overdue task counting, and filtering by project, team, assignee, and status.
- `GET /api/v1/calendar/events`: Flat list of normalized timeline events (both tasks and projects) with color coding, priority badges, and deadline flags.
- `GET /api/v1/calendar/upcoming`: Urgent deadline countdown endpoint listing items due in the next N days sorted by days remaining.

### 13. Workspace Dashboard & Analytics API (`/api/v1/dashboard`, `/api/v1/projects/{id}/analytics`, `/api/v1/teams/{id}/analytics`)

- `GET /api/v1/dashboard/overview`: High-performance SQL aggregation returning total/active/completed projects, total/completed/in-progress/overdue tasks, upcoming deadlines, total team members, and personal task summaries.
- `GET /api/v1/dashboard/task-stats`: Workspace task distribution breakdown across statuses, priority levels, completion rates, and estimated vs actual hours.
- `GET /api/v1/dashboard/project-stats`: Per-project health metrics including task counts, completion percentages, budget utilization, and overdue indicators.
- `GET /api/v1/dashboard/team-stats`: Organization-wide member workload distribution computing task ownership, pending counts, and percentage workload shares.
- `GET /api/v1/dashboard/recent-activity`: Real-time audit activity feed for the dashboard.
- `GET /api/v1/projects/{project_id}/analytics`: Single-project analytics deep dive with status/priority distributions, completion percentages, and days remaining.
- `GET /api/v1/teams/{team_id}/analytics`: Single-team workload and delivery velocity analytics.

---

## Running Tests

Execute the automated test suite with pytest:

```bash
pytest -v
```

Tests cover:
- Application liveness and readiness probes (`/api/v1/health`)
- Supabase JWT cryptographic decoding, asymmetric ES256 verification, and claim validation (`test_auth.py`)
- Organization creation, subscription security, RBAC hierarchy, sole-owner protection, and workspace preferences (`test_organizations.py`)
- Functional team CRUD, team leads, and member assignment lifecycles (`test_teams.py`)
- Project containers, key derivation/collision protection, status/team filtering, and budget tracking (`test_projects.py`)
- 16-table relational schema constraints, compound foreign keys, and cascading delete isolation (`test_complete_schema.py`)
- Model definitions and migration safety simulations (`test_phase1_models.py`)
