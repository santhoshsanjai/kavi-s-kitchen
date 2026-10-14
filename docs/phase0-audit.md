# Kavi's Kitchen: Phase 0 Repository Audit

Audit date: 14 Oct 2026. Audited commit: `baf0492` on `main` (latest commit 15 Sep 2026).
Target spec: *Kavis Kitchen Application Requirements & Coding Agent Specification v2.0* (14 Oct 2026).

No feature code was changed in Phase 0. Every status below cites files, endpoints or tests in this repository.

---

## 1. Headline findings

1. **The backend runs on MongoDB, not PostgreSQL.** `backend/app/core/database.py` uses `motor` (async MongoDB) and silently falls back to an in-memory `mongomock-motor` database when Atlas is unreachable. There is no SQL schema, no ORM and no migrations. The v2.0 spec requires PostgreSQL with NUMERIC money, foreign keys, unique constraints and transactions. Moving to PostgreSQL is a major database redesign and needs owner approval (Decision A).
2. **There are no mobile apps.** The repo has one React web app (`frontend/`). The "driver app" is a web route (`/driver/today`, `frontend/src/pages/driver/DriverTodayPage.tsx`). The customer app does not exist in any form, and there is no customer login (no OTP, no customer role).
3. **Several protected operations have no backend authorization.** Any logged-in user, including a driver, can read any order, change any order's status, and complete or fail orders not assigned to them. Both WebSocket endpoints accept unauthenticated connections. Details in Section 6.
4. **Most of the v2.0 domain does not exist yet:** service calendar/holidays, subscriptions, meal slots, skips and credits, weekly menus, accept/decline/5-minute expiry, trips and route legs, driver earnings, payments, ledger, invoices, settings, audit log and inbox.
5. **What exists and works:** admin/driver password login with JWT, admin CRUD for customers, enquiries and meal plans, a daily order list with "generate daily orders", bulk driver assignment with stop sequence, driver start/deliver/fail actions, and a live GPS tracking map. The backend test suite passes (4/4) and the frontend type-checks and builds.

## 2. Current architecture

| Area | What is there | Evidence |
|---|---|---|
| Layout | Single repo: `backend/` (FastAPI) + `frontend/` (React web) | repo root |
| Backend | FastAPI (unpinned), Pydantic v2, pydantic-settings, python-jose (JWT HS256), bcrypt | `backend/requirements.txt`, `backend/app/main.py` |
| Database | MongoDB via `motor`; automatic fallback to `mongomock-motor` in-memory DB | `backend/app/core/database.py` |
| Migrations | None. Indexes created ad hoc at startup for `users` only | `backend/app/db/init_db.py:18-20` |
| Seed data | Seeds 3 users with fixed passwords, 5 meal plans, customers and enquiries on **every startup in every environment** | `backend/app/db/init_db.py`, called from `backend/app/main.py:12` |
| API prefix | `/api/v1` with routers auth, customers, enquiries, meal-plans, orders, drivers, tracking | `backend/app/api/v1/api.py` |
| Frontend | React 19, Vite 8, TypeScript 6, Redux Toolkit + RTK Query, react-router 7, Tailwind 3 + shadcn/ui, lucide-react, recharts, date-fns, zod | `frontend/package.json` |
| Mobile | None | — |
| Deployment | No Dockerfile, docker-compose, CI workflow or deploy config. README covers local dev only | repo root, `README.md` |
| Older spec | `kavis-kitchen-coding-agent.md` (MongoDB Atlas, web-only, live GPS tracking). It conflicts with v2.0 on database, apps and pricing model | repo root |

### Theme tokens (to preserve)

Defined as HSL CSS variables in `frontend/src/index.css` and mapped in `frontend/tailwind.config.js` (shadcn convention):

| Token | Light | Dark |
|---|---|---|
| `--background` | `48 40% 98%` warm cream | `0 0% 10%` charcoal |
| `--foreground` | `0 0% 20%` charcoal | `48 40% 96%` cream |
| `--primary` | `45 93% 47%` mustard/gold | same |
| `--secondary` | `142 65% 24%` deep green | same |
| `--ring` | mustard | mustard |
| `--radius` | `0.5rem` | — |

Pages also use Tailwind `stone-*`/`amber-*` utility colors directly, with `font-serif` headings. Logo: `frontend/src/assets/logo.png`. The React Native apps should take these same values as a shared token file.

### Admin/driver routes (`frontend/src/App.tsx`)

| Route | Page | Data source |
|---|---|---|
| `/login` | `pages/auth/LoginPage.tsx` | `POST /auth/login` |
| `/admin/dashboard` | `pages/admin/DashboardPage.tsx` | **Hard-coded numbers** (`quickStats`, lines 21-50); no API call |
| `/admin/customers` | `pages/admin/CustomersPage.tsx` | `/customers` |
| `/admin/enquiries` | `pages/admin/EnquiriesPage.tsx` | `/enquiries` |
| `/admin/meal-plans` | `pages/admin/MealPlansPage.tsx` | `/meal-plans` |
| `/admin/meal-planner` | `pages/admin/MealPlannerPage.tsx` | `/orders` for **one date** (daily list, not a monthly grid) |
| `/admin/deliveries` | `pages/admin/DeliveriesPage.tsx` | `/orders`, `/orders/bulk-assign`, `/drivers` |
| `/admin/live-tracking` | `pages/admin/LiveTrackingPage.tsx` | `/tracking/live-drivers` + `ws /tracking/ws/admin` |
| `/admin/drivers` | `pages/admin/DriversPage.tsx` | `/drivers` |
| `/admin/users`, `/admin/reports`, `/admin/settings` | `ModulePlaceholderPage` | placeholders only |
| `/driver/today` (`/completed`, `/profile` render the same page) | `pages/driver/DriverTodayPage.tsx` | `/drivers/me/today-deliveries`, order actions, `ws /tracking/ws/driver/{id}` |

### API inventory

| Endpoint | Guard | Notes |
|---|---|---|
| `POST /auth/login`, `POST /auth/refresh` | public | login by username/email/phone + password; no rate limit |
| `GET /auth/me`, `POST /auth/logout` | any user | logout is a no-op (no token revocation) |
| `GET/POST /customers`, `GET/PUT/DELETE /customers/{id}`, `PATCH /customers/{id}/status` | admin | DELETE is a hard delete |
| `GET/POST /enquiries`, `GET/PUT/DELETE /enquiries/{id}`, `POST /enquiries/{id}/convert` | admin | convert creates/links a customer, not an order |
| `GET /meal-plans`, `GET /meal-plans/{id}` | any user | |
| `POST/PUT/DELETE /meal-plans...` | admin | hard delete; price is `float` |
| `GET /orders` | any user; drivers filtered to own | daily summary counts are computed over all orders for the date, including for drivers |
| `POST /orders/generate-daily` | admin | one order per active customer × preferred session; skips existing customer+date+session (check-then-insert, no unique index) |
| `POST /orders`, `PUT/DELETE /orders/{id}`, `PATCH /orders/bulk-status`, `POST /orders/bulk-assign` | admin | |
| `GET /orders/{id}` | **any user, no ownership check** | |
| `PATCH /orders/{id}/status` | **any user, no ownership check** | |
| `POST /orders/{id}/start-delivery`, `/complete-delivery`, `/fail-delivery` | **any user, no assignment check** | no state checks; repeat calls re-complete |
| `GET /drivers` | any user | drivers can list all drivers |
| `GET /drivers/me/today-deliveries`, `PATCH /drivers/me/status` | any user | "today" computed in UTC |
| `PATCH /drivers/{id}`, `PATCH /drivers/{id}/status` | admin | updates any user record, not only drivers |
| `GET /tracking/live-drivers` | any user | returns customer names/phones/addresses of active orders |
| `WS /tracking/ws/driver/{driver_id}` | **none** | anyone can push positions as any driver |
| `WS /tracking/ws/admin` | **none** | anyone can subscribe to the live feed |
| `GET /health` | public | always reports `"database": "connected"` |

### Data model (MongoDB collections)

`users` (role SUPER_ADMIN/ADMIN/DRIVER, driver fields inline: `driving_status`, vehicle, `last_latitude/longitude`), `customers` (embedded `address` with lat/lng/place_id and `meal_preference`), `enquiries`, `meal_plans` (`price` float, `service_days` 26, `meal_sessions`), `orders` (one doc per customer/date/session; driver assignment, `sequence_number`, `delivery_charge`, `total_price` all inline). Helpers in `backend/app/models/*.py`; schemas in `backend/app/schemas/*.py`. There is no customer-user link, no driver code, no subscription, slot, task, trip, ledger or payment collection.

### Tests

| File | Covers |
|---|---|
| `backend/tests/test_auth_endpoints.py` | login, /me, refresh, bad password → 401 |
| `backend/tests/test_customer_and_meal_endpoints.py` | customer + meal-plan CRUD happy path |
| `backend/tests/test_order_and_assignment_endpoints.py` | generate-daily, bulk assign |
| `backend/tests/test_tracking_and_driver_lifecycle.py` | driver start/complete flow, live drivers |

Result on this audit: `pytest -q` → **4 passed** (run against the in-memory mock DB). There are no negative authorization tests, no frontend tests and no end-to-end tests. Frontend: `tsc -b` clean, `vite build` succeeds (573 kB bundle warning), `oxlint` 6 warnings, 0 errors.

## 3. Feature matrix (v2.0 requirements vs. repository)

States: **Implemented**, **Partially Implemented**, **Missing**, **Broken**, **Needs Verification**.

### Platform and security

| Requirement | Status | Evidence / gap |
|---|---|---|
| FastAPI backend | Implemented | `backend/app/main.py` |
| PostgreSQL database | Missing | MongoDB only (`core/database.py`) |
| Migrations | Missing | none |
| NUMERIC/Decimal money | Missing | `float` in `schemas/meal_plan.py:11`, `schemas/order.py:45-46`, `schemas/enquiry.py:28` |
| Admin password login + JWT access/refresh | Implemented | `endpoints/auth.py`, `core/security.py`, `tests/test_auth_endpoints.py` |
| Role-based permissions | Partially Implemented | coarse `require_roles` (`api/deps.py:63`); `ROLE_PERMISSIONS` list returned to the UI but never enforced server-side |
| Backend authorization on every protected operation | Broken | see Section 6 |
| Login rate limiting / OTP abuse protection | Missing | no limiter anywhere |
| Token revocation on logout | Missing | `endpoints/auth.py` logout is a no-op |
| Secrets out of source control | Partially Implemented | `.env` gitignored; but seeded default passwords are in `init_db.py` and README and are created in every environment |
| Timezone-aware, Asia/Kolkata business dates | Broken | "today" uses UTC (`endpoints/drivers.py`, `endpoints/orders.py` `datetime.now(timezone.utc).strftime(...)`), so 00:00-05:30 IST shows the previous day |
| Audit log | Missing | none |
| Health check | Needs Verification | `/health` hard-codes `"connected"` and hides mock-DB fallback |
| Deployment configuration | Missing | no Docker/CI/deploy files |

### Admin web

| Requirement | Status | Evidence / gap |
|---|---|---|
| Dashboard with live counts, alerts, filters | Broken | `DashboardPage.tsx:21-50` shows hard-coded numbers; no alerts |
| Customer master CRUD + deactivate | Implemented | `endpoints/customers.py`, `CustomersPage.tsx`, `tests/test_customer_and_meal_endpoints.py` (hard delete also exposed) |
| Customer fields: alt phone, landmark, instructions, preferences, notes | Partially Implemented | `schemas/customer.py`; no email, no access instructions field, no audit fields beyond timestamps |
| Map-based location (Google Places/Geocoding) | Broken | `components/maps/LocationPickerModal.tsx` is a simulated map with 10 hard-coded Chennai points and a fabricated `google_place_id` (line 109); no Google API is called |
| Manual address fallback | Implemented | address fields in `CustomersPage.tsx` / `AddressSchema` |
| Plan configuration (name, type, price, slots) | Partially Implemented | `endpoints/meal_plans.py`; no active dates, no rate versioning; seed prices 5499/6499 differ from spec's 5500/6299 |
| Subscription by service month | Missing | no subscription model |
| Service calendar (Sundays/holidays excluded, configurable) | Missing | `service_days: 26` is a static number on the plan |
| Monthly meal calendar grid | Missing | `MealPlannerPage.tsx` is a single-day order list |
| Skip/restore meal or full day, cutoffs, credits | Missing | only a raw `SKIPPED` order status (`schemas/order.py:93`) settable via status PATCH; no cutoff, credit or audit |
| Menu/food master, weekly published menu | Missing | none |
| Inquiries: create, track, convert | Partially Implemented | `endpoints/enquiries.py`; convert creates a customer only, no confirmed order, no price/delivery-fee confirmation, hard delete |
| One-time order creation/confirmation | Partially Implemented | `POST /orders` with `order_type: AD_HOC`; no pending→confirmed workflow, no order lines |
| Driver create/deactivate, unique driver codes | Partially Implemented | edit/deactivate via `PATCH /drivers/{id}`; no create endpoint (drivers exist only by seeding), no driver code |
| Task assignment + stop sequence | Partially Implemented | `POST /orders/bulk-assign` sets driver + `sequence_number`; no per-trip grouping, no assignment history |
| Assignment response timer / decline / reassignment | Missing | none |
| Settings (rates, cutoffs, holidays, rounding, versioning) | Missing | `/admin/settings` placeholder; env vars `FREE_DELIVERY_RADIUS_KM`, `MIN_DELIVERY_CHARGE`, `*_DROP_PAYOUT` are defined in `core/config.py` but unused |
| Payments, ledger, invoices/receipts | Missing | none |
| Reports and CSV/Excel/PDF export | Missing | `/admin/reports` placeholder |
| Live GPS tracking map | Implemented (not in v2.0 scope) | `LiveTrackingPage.tsx`, `endpoints/tracking.py`; insecure (Section 6) |

### Driver app

| Requirement | Status | Evidence / gap |
|---|---|---|
| React Native app (Android/iOS) | Missing | web page only |
| Driver login | Partially Implemented | shared password login; no driver code |
| Task inbox, only own tasks | Partially Implemented | `GET /drivers/me/today-deliveries` filters by driver; but `GET /orders/{id}` exposes any order |
| Accept/decline individual tasks, 5-minute expiry | Missing | none |
| Trip start/end per meal window | Missing | per-order `start-delivery` only |
| Delivered with note | Implemented | `POST /orders/{id}/complete-delivery`; but no ownership/state/idempotency check |
| Failed with reason → admin alert | Partially Implemented | `fail-delivery` requires reason, broadcasts over WS; no persistent admin alert |
| Partial delivery (delivered vs missing items) | Missing | none |
| Route legs, Maps distances, earnings, day close | Missing | none |
| Navigation hand-off to Google Maps | Implemented | `DriverTodayPage.tsx:215-218` opens maps URL |

### Customer app

| Requirement | Status | Evidence / gap |
|---|---|---|
| React Native app | Missing | none |
| Mobile + OTP login, customer role | Missing | `UserRole` has no CUSTOMER (`schemas/user.py:7`) |
| Profile, subscription, menu, request flow, inbox, history, balance | Missing | none |

## 4. Proposed phased plan

Follows Section 13 of the spec, with one adjustment: a **Phase 0.5 foundation** step, because Phase 1 cannot add NUMERIC money, unique constraints and transactional ledgers on the current MongoDB layer without first settling the database question.

| Phase | Scope | Exit gate |
|---|---|---|
| **0.5 Foundation** (after Decision A) | PostgreSQL + SQLAlchemy 2 (async) + Alembic; port existing users/customers/enquiries/meal_plans/orders models and endpoints with the same URLs and response shapes so the admin web keeps working; Postgres test DB in pytest; close the Section 6 authorization holes; IST date helper; stop seeding default passwords outside development | existing 4 tests + new authz tests green on Postgres; admin web works unchanged |
| **1 Domain and calculations** | settings with effective-dated versions; service calendar/holidays; plans + rate versions; subscriptions + meal slots; proration/skip-credit service; inquiry→order→order lines; delivery task + assignment state machine with 5-minute expiry job; trips + route legs (Maps client behind an interface, with recorded source); payout policy versions + earning lines; customer ledger + payments; audit log; unit tests first | calculation and state-machine unit tests green |
| **2 Admin operations** | customer location with real Places/Geocoding; plans/settings UI; weekly menus; monthly meal grid with skip/restore and credit preview; inquiry confirmation; task assignment + stop order + timers; payments/invoices; live dashboard + alerts | API integration tests + manual QA |
| **3 Driver app** | Expo React Native app: driver-code login, inbox, accept/decline, trips, deliver/fail/partial, distance + earnings summary | role tests: driver sees only assigned data |
| **4 Customer app** | Expo React Native app: OTP login (provider behind interface), home, menu, subscription calendar, requests, inbox, balance | role tests: customer sees only own data |
| **5 Integration and QA** | E2E across clients; duplicate submissions, poor network, cutoffs, partial delivery, payouts | critical E2E green |
| **6 Release readiness** | Docker/deploy config, backups, logging, mobile signing, rollback notes, acceptance checklist | owner sign-off |

Proposed repo layout additions: `apps/customer/` and `apps/driver/` (Expo), `packages/` for shared TS types/theme tokens, `backend/alembic/`. The existing `frontend/` stays as the admin web.

## 5. Schema/API compatibility risks

1. **MongoDB → PostgreSQL** replaces every data-access line in all 7 routers and changes ID format (ObjectId strings → UUID or integer). Mitigation: keep URLs and JSON shapes; IDs stay strings in JSON. Needs to know whether any real data lives in Atlas today (if yes, a one-off export/import script).
2. **`orders` conflates three v2.0 entities** (subscription meal slot, one-time order, delivery task). Splitting them changes `/orders` semantics used by `MealPlannerPage`, `DeliveriesPage` and `DriverTodayPage`. Mitigation: keep `/orders` as a read-compatible view during Phase 2, then retire.
3. **Order status enum differs** from v2.0 states (`PLANNED/PREPARING/READY/OUT_FOR_DELIVERY` vs `Assigned/Accepted/En Route/Delivered/Failed/Partial`, plus `ReassignmentNeeded`). Frontend badges and filters must be updated together with the backend.
4. **Floats for money** in plans, enquiries and orders. Converting to NUMERIC changes JSON from numbers to strings (or rounded numbers); the frontend types in `frontend/src/types/*.ts` must follow.
5. **Plan model change**: `service_days: 26` becomes a planning default; actual slot count comes from the generated calendar. `meal_sessions` becomes included meal slots with rate versions.
6. **Customer location** currently stores fabricated place IDs from the simulated picker. Existing records' coordinates should be treated as unverified.
7. **Driver identity** lives on `users`; adding `driver_code` and a separate `Driver` profile changes `/drivers` responses.
8. **Live GPS tracking** is not in v2.0. Keeping it adds location-privacy obligations; removing it removes a working screen (Decision C).
9. **Older spec file** `kavis-kitchen-coding-agent.md` will mislead future contributors; mark it superseded once v2.0 is approved.

## 6. Security defects found (fix in Phase 0.5)

| # | Defect | Evidence |
|---|---|---|
| S1 | Any authenticated user can read any order (customer name, phone, address) | `GET /orders/{order_id}` uses `get_current_active_user` only (`endpoints/orders.py:214`) |
| S2 | Any authenticated user can set any order's status | `PATCH /orders/{order_id}/status` (`endpoints/orders.py:272`) |
| S3 | Any authenticated user can start/complete/fail any order, repeatedly, from any state | `endpoints/orders.py:414`, `:488`, `:571`; no `assigned_driver_id` or state check |
| S4 | Unauthenticated WebSocket lets anyone impersonate a driver's location and overwrite their stored position | `WS /tracking/ws/driver/{driver_id}` (`endpoints/tracking.py:18`) |
| S5 | Unauthenticated WebSocket streams customer names and addresses to anyone | `WS /tracking/ws/admin` (`endpoints/tracking.py:99`) |
| S6 | Drivers can list all drivers and all live positions with active customers | `GET /drivers` (`endpoints/drivers.py:62`), `GET /tracking/live-drivers` (`endpoints/tracking.py:116`) |
| S7 | Default accounts with published passwords are seeded on every startup in every environment | `db/init_db.py:24-66`, `README.md` |
| S8 | No login rate limiting | `endpoints/auth.py:27` |
| S9 | Silent fallback to an in-memory DB in any environment would lose all writes on restart while `/health` reports "connected" | `core/database.py:31-45`, `main.py:30` |

## 7. Decisions needed before Phase 1

**Repository decisions (from this audit):**

- **A. Database.** Migrate to PostgreSQL as the spec requires (recommended), or stay on MongoDB and accept weaker money/transaction guarantees. Also: is there any real customer data in the MongoDB Atlas database today?
- **B. Mobile stack.** Expo (managed React Native) in `apps/customer` and `apps/driver` (recommended), or bare React Native.
- **C. Live GPS tracking.** Keep (secured, admin-only) or remove since v2.0 does not ask for it. Recommended: keep but secure.

**Spec Section 14 decisions that block Phase 1 calculations:** #3 rounding (per meal vs. final total), #4 fixed allowance period, #5 what counts as one drop, #6 Maps fallback when no route, #7 credit auto-apply and expiry, #11 End Trip validation, #12 Sunday/holiday override, #13 payment allocation.

**Can be configured later (do not block Phase 1):** #1 delivery ₹/km and minimum, #2 return-leg customer charge, #8 GST invoice fields, #9 OTP provider, #10 Maps credentials. #14 is answered by this audit: entry points are `backend/app/main.py` and `frontend/src/main.tsx`, default branch `main`, no deployment target is configured in the repo, and current tests are the 4 backend pytest files above.

## 8. How the audit was verified

```bash
# backend (Python 3.13); unreachable Mongo URI forces the in-memory fallback
cd backend && pip install -r requirements.txt
MONGODB_URI="mongodb://127.0.0.1:1/x" JWT_SECRET_KEY=test python -m pytest -q   # 4 passed

# frontend
cd frontend && npm ci && npx tsc -b && npm run build && npm run lint          # build OK, 6 lint warnings
```
