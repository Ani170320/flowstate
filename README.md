# FLOWSTATE — Backend API Service (FastAPI & Supabase PostgreSQL)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0%20Async-D71F00?style=flat)](https://www.sqlalchemy.org/)
[![PostgreSQL 17](https://img.shields.io/badge/PostgreSQL-17%20(Supabase)-336791?style=flat&logo=postgresql)](https://supabase.com/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-orange?style=flat)](https://alembic.sqlalchemy.org/)

This is the dedicated **`backend`** branch of **FLOWSTATE**, isolating the standalone Python FastAPI REST API service layer.

---

## 🌟 Backend Capabilities

- **Authentication & Multi-Tenant Authorization:** JWT access tokens, bcrypt password hashing, and row-level organization workspace isolation.
- **Auto-Provisioning Invites:** When inviting non-existent email addresses to an organization, accounts are automatically created in both `auth.users` and `public.users`.
- **Task & Kanban Pipeline:** Comprehensive CRUD, status changes, and order reindexing across customizable stages.
- **Task File Attachments:** S3-compatible binary streaming to Supabase Storage with presigned download URLs.
- **SQL-Aggregated Analytics:** Real-time 7-day velocity throughput, 4-week influx vs. completion, cycle time calculations, and team workload distributions.
- **Sprint Calendar Feeds:** Month and week delivery cutoff projections.

---

## 🚀 How to Run the Backend

### 1. Prerequisites
- **Python** >= 3.10 (Recommended: Python 3.12 or 3.13)
- Active **PostgreSQL** or **Supabase** instance

### 2. Navigate & Set Up Virtual Environment
```bash
cd backend

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the sample environment file:
```bash
cp .env.example .env
```
Update `backend/.env` with your PostgreSQL database connection strings:
```env
DATABASE_URL=postgresql+asyncpg://postgres:<PASSWORD>@<SUPABASE_HOST>:5432/postgres
DIRECT_URL=postgresql://postgres:<PASSWORD>@<SUPABASE_HOST>:5432/postgres
SUPABASE_URL=https://<PROJECT_ID>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY>
SECRET_KEY=<SECURE_JWT_SECRET>
```

### 5. Run Database Migrations
```bash
alembic upgrade head
```

### 6. Start the FastAPI Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📖 Interactive API Documentation

Once the server is running, explore and test the endpoints directly in your browser:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Full Markdown API Reference:** See [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) for request/response models and cURL snippets.

---

## 🧪 Running Tests

```bash
# Run full pytest suite
pytest -v
```

---

## 🌿 Related Branches
- [`main`](https://github.com/Ani170320/flowstate/tree/main): Full monorepo containing both frontend and backend.
- [`frontend`](https://github.com/Ani170320/flowstate/tree/frontend): Dedicated Next.js 16 frontend application.
