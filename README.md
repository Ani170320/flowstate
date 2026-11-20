# FLOWSTATE — Enterprise Engineering Operations Platform

[![Next.js 16](https://img.shields.io/badge/Next.js-16%20App%20Router-black?style=flat&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17%20(Supabase)-336791?style=flat&logo=postgresql)](https://supabase.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)

FLOWSTATE is a high-velocity, real-time engineering operations and project intelligence platform designed for engineering leaders, product managers, and agile software development teams. Built as a full-stack system featuring a **Next.js 16** frontend and an async **FastAPI** backend backed by **Supabase PostgreSQL 17**.

---

## 🌟 Key Features

- **Multi-Tenant Organization Workspaces:**
  - Secure tenant isolation with organization switching, role-based access control (`owner`, `admin`, `tech_lead`, `developer`, `viewer`), and auto-provisioning for invited members.
- **AI Workspace Intelligence & Copilot Engine:**
  - **AI Task / PRD Decomposition:** 1-click feature breakdown generating structured subtasks, effort estimations, priority scoring, and labels.
  - **AI Workload & Assignee Recommendation:** Intelligent capacity-aware matching recommending the ideal team member based on active sprint workloads.
  - **AI Workspace Copilot (`⌘J` / `Ctrl+J`):** Floating conversational copilot answering natural-language inquiries on sprint velocity, blockers, and workloads.
  - **AI Sprint Retrospective & Executive Synthesis:** Automated retrospective synthesis highlighting sprint achievements, bottlenecks, and strategic actions with Markdown export.
- **Interactive Kanban & Task Pipelines:**
  - Drag-and-drop task workflow boards (`backlog`, `todo`, `in_progress`, `in_review`, `done`) with real-time status updates and priority scoring (`low`, `medium`, `high`, `urgent`).
- **Task Attachments & Binary Storage:**
  - Native file drag-and-drop support in task detail modals, integrated directly with FastAPI file-streaming endpoints and Supabase Storage buckets.
- **Live Real-Time Multi-Tab Synchronization:**
  - Dual-layer synchronization powered by browser `BroadcastChannel` and page `visibilitychange` listeners. Changes made in one window or device reflect immediately across all open tabs.
- **Engineering Analytics & Velocity Engine:**
  - Dynamically computed 7-day velocity throughput, 4-week influx vs. completion curves, cycle times, critical blocker counts, and team on-time delivery rates (100% computed from real database state).
- **Milestone & Release Calendar:**
  - Month and week view modes tracking project delivery cutoffs, sprint schedules, and task due dates.
- **1-Click CSV Reporting:**
  - Instant export for projects and sprint tasks to CSV format for audit trails and offline reporting.

---

## 🏗️ Architecture & Tech Stack

```
flowstate/
├── src/                          # Next.js 16 Frontend
│   ├── app/                      # App Router (Workspace, Auth, API routes)
│   ├── components/               # UI components (Kanban, Modals, TopNav, Sidebar)
│   ├── context/                  # State Providers (AuthContext, WorkspaceContext, ToastContext)
│   ├── services/                 # API Client service layer (taskService, projectService, etc.)
│   └── types/                    # Shared TypeScript interfaces & models
├── backend/                      # FastAPI Backend
│   ├── alembic/                  # Database migration scripts & revision history
│   ├── app/
│   │   ├── core/                 # App configuration, security, JWT authentication
│   │   ├── database/             # Async SQLAlchemy connection engine
│   │   ├── models/               # Declarative PostgreSQL ORM models
│   │   ├── routes/               # API route endpoints (tasks, projects, auth, dashboard)
│   │   ├── schemas/              # Pydantic v2 validation models
│   │   └── services/             # Storage, notification, and activity services
│   └── tests/                    # Pytest test suite (unit and integration tests)
├── API_DOCUMENTATION.md          # Complete REST API reference & examples
└── README.md
```

> 📖 **API Reference:** For comprehensive request/response payloads, authentication headers, and cURL examples, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

### Technology Matrix
| Layer | Technologies |
| :--- | :--- |
| **Frontend Framework** | Next.js 16 (App Router), React 19, TypeScript |
| **Styling & UI** | Tailwind CSS v4, Lucide React icons, Recharts |
| **Backend Framework** | FastAPI (Python 3.12+), Uvicorn ASGI |
| **ORM & Database** | SQLAlchemy 2.0 (Async), Alembic, Supabase PostgreSQL 17 |
| **Authentication** | JWT (JSON Web Tokens) with passlib / bcrypt password hashing |
| **Cloud Storage** | Supabase Storage (S3-compatible binary file uploads) |

---

## 🚀 Quick Start Guide

### Prerequisites
- **Node.js** >= 18.18.0 & **npm** >= 9.0.0
- **Python** >= 3.10
- **PostgreSQL** or active **Supabase** project

---

### 1. Backend Setup (FastAPI)

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\activate

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Open `backend/.env` and update your database URL and Supabase credentials:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:<YOUR_PASSWORD>@<YOUR_SUPABASE_HOST>:5432/postgres
   DIRECT_URL=postgresql://postgres:<YOUR_PASSWORD>@<YOUR_SUPABASE_HOST>:5432/postgres
   SUPABASE_URL=https://<YOUR_SUPABASE_PROJECT>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=<YOUR_SUPABASE_SERVICE_ROLE_KEY>
   SECRET_KEY=<YOUR_STRONG_SECRET_KEY>
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   > Backend API documentation will be available at:
   > - **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
   > - **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
   > - **Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

*(Windows convenience: you can also double-click `start-backend.bat` in the root folder).*

---

### 2. Frontend Setup (Next.js)

1. Open a new terminal in the project root:
   ```bash
   npm install
   ```

2. Configure frontend environment variables:
   Create a `.env.local` file in the root directory:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   NEXT_PUBLIC_SUPABASE_URL=https://<YOUR_SUPABASE_PROJECT>.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>
   ```

3. Run the Next.js development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Running Tests

### Backend Unit & Integration Tests
```bash
cd backend
.venv\Scripts\activate   # or source .venv/bin/activate
pytest
```

### Frontend Typecheck & Build
```bash
# Verify TypeScript strict compile
npx tsc --noEmit

# Production build
npm run build
```

---

## 🌿 Repository Branch Structure

This repository provides 3 dedicated branches tailored for full-stack and modular development:

| Branch | Description | Link |
| :--- | :--- | :--- |
| **`main`** | **Production Monorepo** — Full stack containing both frontend and backend synchronized. | [`main`](https://github.com/Ani170320/flowstate/tree/main) |
| **`frontend`** | **Frontend Codebase** — Dedicated purely to Next.js 16, UI components, and state layer. | [`frontend`](https://github.com/Ani170320/flowstate/tree/frontend) |
| **`backend`** | **Backend Codebase** — Dedicated purely to the FastAPI service, models, and migrations. | [`backend`](https://github.com/Ani170320/flowstate/tree/backend) |

---

## 🔒 Security & Privacy

- All sensitive keys (`.env`, `.env.local`, API secret keys) are strictly excluded from version control via `.gitignore`.
- Database access enforces row-level multi-tenant context validation on all mutations.
- Passwords are encrypted with `bcrypt` (12 rounds) and tokens are signed with `HS256` JWTs.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
