# Kavi's Kitchen 🍲

A production-ready meal delivery management and kitchen operations web application for **Kavi's Kitchen**.

---

## 🚀 Features

- **Multi-Role Authentication & Access Control (RBAC)**:
  - **Super Admin**: System-wide control, user management, reports, settings, and full operational access.
  - **Kitchen Admin**: Customer master data, meal preferences, daily meal planner, enquiry conversion, and delivery assignment.
  - **Delivery Driver**: Mobile-first portal with sequence orders, live location tracking, and Google Maps handoff.
- **Frontend Architecture**:
  - React 19 + Vite + TypeScript.
  - Redux Toolkit (RTK) Query with auto token refresh on 401.
  - Responsive layouts using Tailwind CSS and `shadcn/ui` components.
  - Configurable brand tokens (Golden Mustard `#E5A93C`, Deep Green `#1B4D3E`, Warm Cream background).
- **Backend Architecture**:
  - Python FastAPI with SQLAlchemy 2 (async, `asyncpg`) on PostgreSQL 16.
  - Alembic migrations (`backend/alembic/`); money stored as `NUMERIC`.
  - Direct bcrypt hashing & JWT token security (Access & Refresh tokens).
  - Demo accounts and data seeded on startup in `ENVIRONMENT=development` only.

---

## 📁 Repository Structure

```text
kavis-kitchen/
├── backend/            # FastAPI Python application
│   ├── app/
│   │   ├── api/        # API routers, endpoints, and auth dependencies
│   │   ├── core/       # Security (JWT, bcrypt), config, and database
│   │   ├── db/         # Seed script and initial data setup
│   │   ├── models/     # Database models & helpers
│   │   └── schemas/    # Pydantic schemas (User, Auth, Token)
│   └── tests/          # Pytest automated test suite
├── frontend/           # React + TypeScript Vite application
│   ├── src/
│   │   ├── app/        # Redux store configuration
│   │   ├── assets/     # Brand logos and static media
│   │   ├── components/ # Shared UI & layouts (Navbar, Sidebar, ProtectedRoute)
│   │   ├── features/   # RTK Query API slice & Auth slice
│   │   └── pages/      # Auth (Login), Admin Dashboard, and Driver views
├── .env.example        # Environment variable template
└── README.md
```

---

## 🛠️ Quick Start

### 1. Database (PostgreSQL)

Start a local PostgreSQL 16 with Docker:

```bash
docker compose up -d db
```

This creates the `kavis_kitchen` database and the `kavis_kitchen_test` database used by the tests (user `kavis`, password `kavis`, port 5432).

Without Docker, install PostgreSQL 16 and run:

```bash
psql -U postgres -c "CREATE USER kavis WITH PASSWORD 'kavis' CREATEDB;"
psql -U postgres -c "CREATE DATABASE kavis_kitchen OWNER kavis;"
psql -U postgres -c "CREATE DATABASE kavis_kitchen_test OWNER kavis;"
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # On Windows (or source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
cp .env.example .env     # DATABASE_URL already points at the local database
alembic upgrade head     # create/upgrade the schema
uvicorn app.main:app --reload --port 8000
```

Run the tests (they rebuild the schema in `kavis_kitchen_test`; override with `TEST_DATABASE_URL`):

```bash
pytest -q
```

After changing models, create a migration with `alembic revision --autogenerate -m "describe change"` and review it before committing.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit **`http://localhost:5173`** to access the login page.

---

## 🔑 Default Accounts (Development Pre-seeded)

| Role | Username / Identifier | Password | Access Path |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `superadmin` | `Admin@123` | `/admin/dashboard` |
| **Kitchen Admin** | `kitchenadmin` | `Kitchen@123` | `/admin/dashboard` |
| **Driver 1** | `driver1` | `Driver@123` | `/driver/today` |
