# FLOWSTATE — REST API Documentation

Comprehensive reference documentation for the **FLOWSTATE** backend REST API. Built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, and **Supabase PostgreSQL 17**.

---

## 🌐 Base URL & Conventions

- **Base URL:** `http://localhost:8000/api/v1`
- **Interactive OpenAPI Documentation (Swagger UI):** [`http://localhost:8000/docs`](http://localhost:8000/docs)
- **Alternative Documentation (ReDoc):** [`http://localhost:8000/redoc`](http://localhost:8000/redoc)
- **Content-Type:** `application/json` (except file uploads which use `multipart/form-data`)

---

## 🔐 Authentication & Tenant Headers

All protected endpoints require a JWT Bearer token obtained from `/auth/login` or `/auth/signup`. Multi-tenant endpoints also accept an optional `X-Organization-Id` header to explicitly scope requests to a specific organization.

```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
X-Organization-Id: <ORGANIZATION_UUID>   # Optional: defaults to active organization
```

### Standard Error Responses
| Status Code | Code / Error | Description |
| :--- | :--- | :--- |
| **400** | `BAD_REQUEST` | Validation error or malformed payload |
| **401** | `UNAUTHORIZED` | Missing, invalid, or expired JWT token |
| **403** | `FORBIDDEN` | Insufficient permissions within the active organization |
| **404** | `NOT_FOUND` | Requested entity does not exist |
| **409** | `CONFLICT` | Resource conflict (e.g. email already exists) |
| **500** | `INTERNAL_SERVER_ERROR` | Unexpected server failure |

---

## 📑 API Modules

- [1. Authentication & Session](#1-authentication--session)
- [2. Organizations & Members](#2-organizations--members)
- [3. Projects & Initiatives](#3-projects--initiatives)
- [4. Tasks & Kanban Pipeline](#4-tasks--kanban-pipeline)
- [5. Task Subtasks Checklist](#5-task-subtasks-checklist)
- [6. Task Discussion & Comments](#6-task-discussion--comments)
- [7. Task Attachments (Supabase Storage)](#7-task-attachments-supabase-storage)
- [8. Teams & Workload](#8-teams--workload)
- [9. Engineering Analytics & Dashboard](#9-engineering-analytics--dashboard)
- [10. Release & Sprint Calendar](#10-release--sprint-calendar)
- [11. Activity Stream & Audit Log](#11-activity-stream--audit-log)
- [12. Notifications](#12-notifications)
- [13. System Health](#13-system-health)
- [14. AI Intelligence & Copilot Engine](#14-ai-intelligence--copilot-engine)

---

## 1. Authentication & Session

### `POST /auth/signup`
Register a new user account, hash the password, and auto-provision their primary personal organization workspace.

**Request Body:**
```json
{
  "name": "Jane Doe",
  "email": "jane@company.com",
  "password": "StrongPassword123!",
  "phone": "+1-555-0199",
  "workspace_name": "Acme Engineering",
  "workspace_slug": "acme-eng",
  "plan": "enterprise"
}
```

**Response (`201 Created`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1",
    "name": "Jane Doe",
    "email": "jane@company.com",
    "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=Jane%20Doe",
    "role": "owner"
  },
  "active_organization": {
    "id": "e4a2d891-23bc-48d1-9f33-7a2e8c459b12",
    "name": "Acme Engineering",
    "slug": "acme-eng",
    "role": "owner"
  }
}
```

---

### `POST /auth/login`
Authenticate with email and password to receive a signed JWT token.

**Request Body:**
```json
{
  "email": "jane@company.com",
  "password": "StrongPassword123!"
}
```

**Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1Ni...",
  "token_type": "bearer",
  "user": { ... },
  "active_organization": { ... }
}
```

---

### `GET /auth/me`
Retrieve currently authenticated user profile, preferences, and active organization membership.

**Headers:** `Authorization: Bearer <token>`

**Response (`200 OK`):**
```json
{
  "user": {
    "id": "c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1",
    "name": "Jane Doe",
    "email": "jane@company.com",
    "title": "VP of Engineering",
    "department": "Engineering",
    "phone": "+1-555-0199",
    "bio": "Building scalable cloud infrastructure.",
    "avatar_url": "https://...",
    "timezone": "America/New_York",
    "created_at": "2026-11-20T10:00:00Z"
  },
  "active_organization": {
    "id": "e4a2d891-23bc-48d1-9f33-7a2e8c459b12",
    "name": "Acme Engineering",
    "slug": "acme-eng",
    "role": "owner",
    "plan": "enterprise"
  },
  "organizations": [
    {
      "id": "e4a2d891-23bc-48d1-9f33-7a2e8c459b12",
      "name": "Acme Engineering",
      "role": "owner"
    }
  ]
}
```

---

### `PATCH /auth/me`
Update profile fields for the authenticated user.

**Request Body:**
```json
{
  "name": "Jane Doe",
  "title": "Principal Architect",
  "phone": "+1-555-0144",
  "bio": "Specialized in distributed systems."
}
```

---

### `POST /auth/switch-organization`
Switch the user's active organization context.

**Request Body:**
```json
{
  "organization_id": "e4a2d891-23bc-48d1-9f33-7a2e8c459b12"
}
```

---

## 2. Organizations & Members

### `GET /organizations/{org_id}/members`
List all members enrolled in the organization.

**Response (`200 OK`):**
```json
[
  {
    "id": "c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1",
    "role": "owner",
    "user": {
      "id": "c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1",
      "name": "Jane Doe",
      "email": "jane@company.com",
      "title": "VP of Engineering",
      "department": "Engineering",
      "avatar_url": "https://..."
    }
  }
]
```

---

### `POST /organizations/{org_id}/members`
Invite a new member. If the email does not exist in the database, the backend automatically provisions a new account and enrolls them into the organization.

**Request Body:**
```json
{
  "email": "colleague@company.com",
  "role": "developer",
  "name": "Dev Member",
  "department": "Engineering",
  "title": "Software Engineer"
}
```

---

### `PATCH /organizations/{org_id}/members/{user_id}`
Change member role (`owner`, `admin`, `tech_lead`, `developer`, `viewer`).

**Request Body:**
```json
{
  "role": "tech_lead"
}
```

---

### `DELETE /organizations/{org_id}/members/{user_id}`
Remove a member from the organization workspace.

---

## 3. Projects & Initiatives

### `GET /projects`
List all projects within the active organization.

**Response (`200 OK`):**
```json
[
  {
    "id": "99999999-1111-2222-3333-444444444441",
    "key": "FLW",
    "name": "Core Platform Architecture",
    "description": "Multi-tenant engine and real-time synchronization backend.",
    "status": "in_progress",
    "priority": "high",
    "color": "#8B7CFF",
    "progress": 65,
    "budget": 50000,
    "spent": 24000,
    "start_date": "2026-11-01",
    "due_date": "2026-12-15",
    "manager_id": "c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1",
    "team_member_ids": ["c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1"]
  }
]
```

---

### `POST /projects`
Create a new project initiative.

**Request Body:**
```json
{
  "name": "Mobile SDK v2",
  "key": "MSDK",
  "description": "Native iOS & Android client libraries.",
  "status": "planning",
  "priority": "medium",
  "color": "#10B981",
  "start_date": "2026-11-20",
  "due_date": "2026-12-31",
  "budget": 35000
}
```

---

### `GET /projects/{project_id}/analytics`
Retrieve real-time velocity, task distributions, and schedule health for a specific project.

**Response (`200 OK`):**
```json
{
  "project_id": "99999999-1111-2222-3333-444444444441",
  "project_name": "Core Platform Architecture",
  "completion_percentage": 65,
  "total_tasks": 12,
  "completed_tasks": 8,
  "pending_tasks": 4,
  "overdue_tasks_count": 0,
  "estimated_hours_total": 96.0,
  "actual_hours_total": 72.5,
  "tasks_by_status": {
    "todo": 2,
    "in_progress": 2,
    "done": 8
  }
}
```

---

## 4. Tasks & Kanban Pipeline

### `GET /tasks`
Retrieve tasks with flexible filtering.

**Query Parameters:**
| Parameter | Type | Description |
| :--- | :--- | :--- |
| `project_id` | `UUID` | Filter by project |
| `status` | `string` | Filter by `backlog`, `todo`, `in_progress`, `in_review`, `done` |
| `priority` | `string` | Filter by `low`, `medium`, `high`, `urgent` |
| `assignee_id` | `UUID` | Filter by assigned user |
| `search` | `string` | Case-insensitive title and key search |

---

### `POST /tasks`
Create a new task ticket.

**Request Body:**
```json
{
  "project_id": "99999999-1111-2222-3333-444444444441",
  "title": "Implement Redis Cache Cluster",
  "description": "Deploy redis cache for hot organization membership queries.",
  "status": "todo",
  "priority": "high",
  "assignee_id": "c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1",
  "due_date": "2026-11-28",
  "estimated_hours": 12
}
```

---

### `PATCH /tasks/{task_id}`
Update task status (drag-and-drop on Kanban board), priority, assignee, or order index.

**Request Body:**
```json
{
  "status": "in_progress",
  "order": 0
}
```

---

## 5. Task Subtasks Checklist

- `POST /tasks/{task_id}/subtasks` — Add subtask: `{"title": "Write unit tests"}`
- `PATCH /tasks/{task_id}/subtasks/{subtask_id}` — Toggle completion: `{"completed": true}`
- `DELETE /tasks/{task_id}/subtasks/{subtask_id}` — Delete subtask

---

## 6. Task Discussion & Comments

- `GET /tasks/{task_id}/comments` — List all comments in chronological order.
- `POST /tasks/{task_id}/comments` — Post comment: `{"content": "PR is ready for review: #142"}`
- `DELETE /comments/{comment_id}` — Delete comment.

---

## 7. Task Attachments (Supabase Storage)

### `POST /tasks/{task_id}/attachments`
Upload a binary file attachment. Files are streamed to Supabase Storage and registered in PostgreSQL.

**Headers:**
- `Content-Type: multipart/form-data`

**Form Data:**
- `file`: `<BINARY_DATA>` (e.g. PDF, PNG, JPG, CSV, ZIP up to 25MB)

**Response (`201 Created`):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "architecture-diagram.png",
  "file_size": 245120,
  "mime_type": "image/png",
  "download_url": "https://<supabase-host>/storage/v1/object/public/attachments/...",
  "created_at": "2026-11-20T14:30:00Z"
}
```

- `GET /tasks/{task_id}/attachments` — List attachments for a task.
- `DELETE /attachments/{attachment_id}` — Delete attachment record and remove binary file from Supabase Storage.

---

## 8. Teams & Workload

- `GET /teams` — List teams within the organization.
- `POST /teams` — Create a new team (`name`, `description`, `lead_id`, `member_ids`).
- `GET /teams/{team_id}/analytics` — Team workload percentage, active task count, and efficiency.
- `POST /teams/{team_id}/members` — Add member to team.
- `DELETE /teams/{team_id}/members/{user_id}` — Remove member from team.

---

## 9. Engineering Analytics & Dashboard

### `GET /dashboard/overview`
High-level executive metrics for top-of-funnel operational visibility:
```json
{
  "total_projects": 4,
  "active_projects": 3,
  "completed_projects": 1,
  "total_tasks": 28,
  "completed_tasks": 19,
  "in_progress_tasks": 6,
  "overdue_tasks": 1,
  "upcoming_deadlines": 5,
  "total_team_members": 6
}
```

### `GET /dashboard/task-stats`
Aggregated pipeline breakdown:
- Tasks by status (`todo`, `in_progress`, `in_review`, `done`)
- Tasks by priority (`urgent`, `high`, `medium`, `low`)
- Total estimated vs actual hours worked

---

## 10. Release & Sprint Calendar

### `GET /calendar?view=month&date=2026-11-20`
Monthly or weekly calendar feed mapping deliverables and milestone cutoffs:
```json
{
  "view": "month",
  "start_date": "2026-11-01",
  "end_date": "2026-11-30",
  "total_events": 14,
  "days": [
    {
      "date": "2026-11-28",
      "events_count": 2,
      "events": [
        {
          "id": "task_1",
          "entity_type": "task",
          "title": "Implement Redis Cache Cluster",
          "date": "2026-11-28",
          "priority": "high",
          "status": "todo",
          "is_overdue": false
        }
      ]
    }
  ]
}
```

---

## 11. Activity Stream & Audit Log

- `GET /organizations/{org_id}/activities?limit=30` — Paginated organization activity audit trail (task creation, updates, column transitions, comments, and project milestones).

---

## 12. Notifications

- `GET /notifications` — List active notifications for the user.
- `PATCH /notifications/{id}/read` — Mark notification as read.
- `PATCH /notifications/read-all` — Mark all user notifications as read.

---

## 13. System Health

### `GET /health`
Probe server availability and system uptime:
```json
{
  "status": "healthy",
  "application": "FLOWSTATE",
  "version": "1.0.0"
}
```

---

## 14. AI Intelligence & Copilot Engine

Advanced workspace reasoning powered by Google Gemini and OpenAI with intelligent client-aware fallback heuristics.

### `POST /ai/subtasks`
Decomposes a high-level task title or PRD requirement into structured subtasks, estimated hours, priority, and relevant tags.

**Request Body:**
```json
{
  "title": "Implement Stripe Subscription Billing & Webhooks",
  "description": "Customer payment processing with automated invoice receipt",
  "labels": ["Billing", "Backend"]
}
```

**Response (`200 OK`):**
```json
{
  "suggested_title": "Implement Stripe Subscription Billing & Webhooks",
  "description": "Enterprise implementation for Customer payment processing with automated invoice receipt.",
  "estimated_hours": 16,
  "priority": "high",
  "subtasks": [
    { "title": "Design schema & data contracts", "description": null },
    { "title": "Implement core API endpoints and middleware", "description": null },
    { "title": "Integrate frontend UI and state management", "description": null },
    { "title": "Write comprehensive unit and integration tests", "description": null },
    { "title": "Add telemetry, error boundaries, and documentation", "description": null }
  ],
  "labels": ["Billing", "Backend", "AI-Generated"]
}
```

---

### `POST /ai/suggest-assignee`
Recommends the best team member based on active workloads and department skills.

**Request Body:**
```json
{
  "task_title": "Fix UI latency in Kanban drag and drop",
  "task_description": "Optimize React renders and CSS animations",
  "department": "Engineering"
}
```

**Response (`200 OK`):**
```json
{
  "recommended_user_id": "c1f7a288-75d1-4e7a-9a99-b1d6f5f3e9a1",
  "recommended_user_name": "Jane Doe",
  "confidence": 0.88,
  "reasoning": "Jane Doe has high domain skill in Frontend/Engineering and currently has the lowest active task count (2 tasks).",
  "suggested_hours": 6
}
```

---

### `POST /ai/chat`
Answers natural language questions about projects, tasks, bottlenecks, and workloads.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What are the main blockers and urgent tasks in our workspace?"
    }
  ],
  "context_scope": "workspace"
}
```

**Response (`200 OK`):**
```json
{
  "reply": "### 🔍 Workspace Analysis\n\n- **Urgent Blockers:** Found 2 urgent tasks currently in progress.\n- **Velocity:** 18 tasks completed this sprint with an 84% on-time completion rate.",
  "references": null
}
```

---

### `POST /ai/retrospective`
Synthesizes sprint metrics, achievements, bottlenecks, and action items into an executive report.

**Request Body:**
```json
{
  "timeframe_days": 14
}
```

**Response (`200 OK`):**
```json
{
  "summary": "Sprint Retrospective synthesis over the last 14 days shows strong engineering delivery with key opportunities in review turnaround speed.",
  "highlights": [
    "Delivered 14 tasks with 85% sprint completion rate.",
    "0 critical production regressions reported.",
    "Cross-functional alignment maintained."
  ],
  "bottlenecks": [
    "Code review wait times averaged 28+ hours on multi-file PRs.",
    "Dependency wait times on external APIs."
  ],
  "recommendations": [
    "Institute a 4-hour review SLA for high-priority items.",
    "Decompose epics into smaller subtasks under 8 estimated hours.",
    "Conduct mid-sprint capacity check-ins."
  ],
  "markdown_report": "# Sprint Retrospective Report (14-Day Cycle)..."
}
```

