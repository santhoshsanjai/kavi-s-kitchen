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
  - Python FastAPI with async `motor` driver for MongoDB.
  - Direct bcrypt hashing & JWT token security (Access & Refresh tokens).
  - Resilient database connection with Atlas connectivity and in-memory mock fallback for offline development.
  - Auto-seeding of default initial accounts.

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

### 1. Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # On Windows (or source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
cp .env.example .env     # Configure MongoDB and secret keys
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

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
