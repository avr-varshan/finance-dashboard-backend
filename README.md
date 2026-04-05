# Finance Dashboard Backend

> **Live API:** https://finance-dashboard-backend-2-rvrc.onrender.com  
> **Interactive Docs:** https://finance-dashboard-backend-2-rvrc.onrender.com/docs  
> **Database:** Supabase (PostgreSQL)

---

## What is this?

This is a backend system for a finance dashboard — the kind of thing a small finance team would actually use day to day. Different people log in with different roles, work with income and expense records, and see aggregated analytics on a dashboard. The backend handles all of that: who can do what, what the data looks like, and how it gets summarized efficiently.

I built it with **FastAPI**, **async SQLAlchemy**, and **PostgreSQL** — not just because they're popular, but because async I/O matters when you have read-heavy dashboard traffic happening alongside writes and admin operations. The stack is typed end-to-end (Pydantic schemas → ORM models → PostgreSQL), which catches mistakes early and makes the code easy to reason about.

---

## How it maps to the assignment

The assignment asked for six things. Here's exactly what I built for each:

| Assignment requirement | What I built |
|------------------------|--------------|
| **User & role management** | Three roles — `viewer`, `analyst`, `admin`. Full user CRUD for admins: list, fetch by ID, change role, activate/deactivate, activity summary. Registration always creates a `viewer` (by design — more on that below). |
| **Financial records** | Records with amount (`Numeric(12,2)`), type (`income`/`expense`), category, date, and optional notes. Full CRUD with soft delete. Filtering by type, category, date range, amount range, and search. CSV export. |
| **Dashboard APIs** | Five endpoints: summary totals, category breakdown with percentages, monthly/weekly trends, recent transactions, and anomaly alerts (expense spike detection vs trailing average). All aggregated in SQL — not pulled into Python first. |
| **Access control** | Role enforcement via `require_role(...)` FastAPI dependencies on every protected route. Beyond that, viewer-specific query params are stripped at the router level (defense in depth). Notes are redacted based on role even within the same endpoint. |
| **Validation & error handling** | Pydantic v2 models with password strength rules and non-future date checks. A custom `APIException` hierarchy with typed error codes (`INVALID_CREDENTIALS`, `NOT_FOUND`, `SELF_ACTION_FORBIDDEN`, etc.). Every response — success or error — follows a consistent envelope. |
| **Persistence** | PostgreSQL on Supabase, schema managed with Alembic migrations. Token revocation stored in a `RevokedToken` table with JTI tracking. |

### Optional extras I went ahead and built

The assignment listed these as "nice to have." I implemented all of them:

- JWT access + refresh tokens with rotation on refresh
- Server-side token blacklist (logout actually invalidates the token)
- Pagination on listing endpoints
- Search support on records
- Soft delete (records aren't hard deleted — they stay for audit history)
- Rate limiting via slowapi (10 req/min on login, 100 req/min default)
- Integration-style tests with pytest + httpx AsyncClient
- Full OpenAPI docs at `/docs` and `/redoc`
- Seed script with real data and three pre-created users
- Docker Compose scaffolding

---

## Architecture

The folder structure follows a deliberate separation: routers are thin HTTP handlers, services own the business logic and database queries, and models/schemas handle data shape. This isn't just convention — it means the same service function can be called from a router today and a background job or CLI tomorrow without copying logic around.

```
app/
├── main.py          # App factory, middleware, rate limiter, exception handlers
├── config.py        # pydantic-settings (env vars, token lifetimes, secret key validation)
├── database.py      # Async engine, session factory, declarative Base
├── dependencies.py  # get_current_user, require_role — the auth/RBAC backbone
├── models/          # SQLAlchemy ORM: User, FinancialRecord, RecordAuditLog, RevokedToken
├── schemas/         # Pydantic v2 request/response models
├── routers/         # auth, users, records, dashboard, audit, health
├── services/        # All business logic and DB queries live here
├── middleware/       # RBAC middleware factory (alternate require_role)
└── utils/           # Errors, pagination helper, response envelope
alembic/             # Migration history — source of truth for schema
tests/               # pytest-asyncio + httpx AsyncClient test suite
```

### Database schema

<!-- 📸 Add a screenshot of the Supabase schema diagram here -->
> _Screenshot from Supabase schema visualizer — shows the four main tables and their relationships_

![Supabase Schema Diagram](./supabase_schema.png)

The four main tables:

- **`users`** — email, hashed password, role enum, `is_active` flag
- **`financial_records`** — amount (Numeric 12,2), type, category, date, notes, `is_deleted`, `created_by` FK
- **`record_audit_log`** — action, `before_snapshot` (JSON), `after_snapshot` (JSON), user FK, record FK, timestamp
- **`revoked_tokens`** — JTI, expiry — used to validate logout and refresh rotation

---

## Try it live

The API is deployed and seeded. You can hit it right now with these credentials:

| Email | Password | Role |
|-------|----------|------|
| admin@zorvyn.io | Admin@123! | admin |
| analyst@zorvyn.io | Analyst@123! | analyst |
| viewer@zorvyn.io | Viewer@123! | viewer |

**Quickest way to explore:** Open the [interactive docs](https://finance-dashboard-backend-2-rvrc.onrender.com/docs), click "Authorize", use the OAuth2 password flow (`username` = email, `password` = password), and start making requests.

Or with curl:

```bash
# Login and grab a token
curl -s -X POST https://finance-dashboard-backend-2-rvrc.onrender.com/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"analyst@zorvyn.io","password":"Analyst@123!"}' | jq .data.access_token

# Dashboard summary
curl -s 'https://finance-dashboard-backend-2-rvrc.onrender.com/dashboard/summary?period=current_month' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>'

# List records with filters
curl -s 'https://finance-dashboard-backend-2-rvrc.onrender.com/records?type=income&category=Consulting' \
  -H 'Authorization: Bearer <ACCESS_TOKEN>'
```

---

## Run it locally

```bash
git clone <repo-url> && cd finance_backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Fill in DATABASE_URL and a SECRET_KEY (32+ chars)
alembic upgrade head          # Creates the tables
python seed.py                # Seeds users + sample records, prints tokens to console
uvicorn app.main:app --reload
```

Local docs: http://127.0.0.1:8000/docs

Docker is also available — `docker-compose.yml` runs migrations, seed, and uvicorn in one command. Just make sure `DATABASE_URL` and `SECRET_KEY` are set in your environment.

---

## Role permission matrix

This is the exact behavior as implemented — not aspirational spec. A few nuances worth noting:

| Area | Action | viewer | analyst | admin |
|------|--------|:------:|:-------:|:-----:|
| Auth | Register (always creates `viewer`) | ✓ | — | — |
| Auth | Login / Refresh / Logout / Change password | ✓ | ✓ | ✓ |
| Users | View/edit own profile | ✓ | ✓ | ✓ |
| Users | List users / change roles / manage status | — | — | ✓ |
| Records | List records (with role-based restrictions*) | ✓ | ✓ | ✓ |
| Records | View categories / get by ID | ✓ | ✓ | ✓ |
| Records | View audit history for a record | — | ✓ | ✓ |
| Records | Create / Export CSV | — | ✓ | ✓ |
| Records | Update / soft delete | — | — | ✓ |
| Dashboard | Summary (MoM fields hidden for viewer) | ✓* | ✓ | ✓ |
| Dashboard | Categories / Recent transactions | ✓ | ✓ | ✓ |
| Dashboard | Trends / Alerts | — | ✓ | ✓ |
| Audit log | Full log with filters | — | — | ✓ |
| Health | Liveness + readiness checks | open | open | open |

**Viewer restrictions on `GET /records`:** The `created_by`, `search`, and `include_deleted` query params are silently stripped for viewers — they can't filter by creator or see deleted records even if they pass those params. Notes are also `null` in list responses for viewers and analysts (but visible in the per-record detail endpoint for all roles).

---

## API reference

All authenticated routes require `Authorization: Bearer <access_token>`.

### Auth — `/auth`

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/auth/register` | No | Creates user as `viewer`; enforces password strength |
| POST | `/auth/login` | No | JSON login; rate limited 10/min/IP |
| POST | `/auth/token` | No | OAuth2 form for Swagger Authorize button |
| POST | `/auth/refresh` | No | Rotates refresh token; old JTI is blacklisted |
| POST | `/auth/logout` | Yes | Blacklists current access token JTI |
| POST | `/auth/change-password` | Yes | Requires current password |

### Users — `/users`

| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/users/me` | Auth | Own profile |
| PATCH | `/users/me` | Auth | Name only |
| GET | `/users` | admin | Paginated; filter by role, is_active |
| GET | `/users/{id}` | admin | Fetch by UUID |
| PATCH | `/users/{id}/role` | admin | Cannot target self |
| PATCH | `/users/{id}/status` | admin | Cannot deactivate self |
| GET | `/users/{id}/activity` | admin | SQL-aggregated activity stats |

### Records — `/records`

| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/records` | Auth | Type, category, date range, amount range, sort, search, pagination |
| POST | `/records` | analyst, admin | Creates audit log entry |
| GET | `/records/categories` | Auth | Distinct categories (non-deleted only) |
| GET | `/records/export` | analyst, admin | Streaming CSV |
| GET | `/records/{id}` | Auth | Full record including notes |
| PATCH | `/records/{id}` | admin | Partial update + audit snapshot |
| DELETE | `/records/{id}` | admin | Soft delete + audit snapshot |
| GET | `/records/{id}/history` | analyst, admin | Audit trail for one record |

### Dashboard — `/dashboard`

| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/dashboard/summary` | Auth | `period`: current_month, last_month, all_time |
| GET | `/dashboard/categories` | Auth | Income/expense by category with `%` |
| GET | `/dashboard/trends` | analyst, admin | `view`: monthly or weekly |
| GET | `/dashboard/recent` | Auth | `limit` 1–50; notes hidden for viewers |
| GET | `/dashboard/alerts` | analyst, admin | Expense spike, largest txn, stale data alerts |

### Audit — `/audit`

| Method | Path | Role | Notes |
|--------|------|------|-------|
| GET | `/audit/audit-log` | admin | Filter by record, user, action, date range, pagination |

### Health — `/health`

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/health` | No | Liveness check |
| GET | `/health/ready` | No | DB connectivity check |

---

## Response shape

Every response follows a consistent envelope, so the frontend always knows where to look:

```json
// Success
{ "success": true, "data": { ... }, "message": "Record created" }

// Validation error (422)
{ "error": true, "code": "VALIDATION_ERROR", "message": "...", "request_id": "...", "details": [...] }

// API error (401, 403, 404, etc.)
{ "error": true, "code": "NOT_FOUND", "message": "Record not found", "request_id": "..." }
```

Rate limit errors (429) use slowapi's default format, which differs slightly from the envelope above — this is a known limitation noted in the improvements section.

---

## Example requests

**Register a new user**
```bash
curl -s -X POST https://finance-dashboard-backend-2-rvrc.onrender.com/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"new@example.com","password":"Strong1!abc","full_name":"New User"}'
```

**Create a financial record** *(analyst or admin)*
```bash
curl -s -X POST https://finance-dashboard-backend-2-rvrc.onrender.com/records \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"amount":"1250.50","type":"income","category":"Consulting","date":"2026-03-15","notes":"Project A"}'
```

**Get dashboard summary**
```bash
curl -s 'https://finance-dashboard-backend-2-rvrc.onrender.com/dashboard/summary?period=current_month' \
  -H 'Authorization: Bearer <TOKEN>'
```

**Export records as CSV**
```bash
curl -s -o records.csv 'https://finance-dashboard-backend-2-rvrc.onrender.com/records/export' \
  -H 'Authorization: Bearer <TOKEN>'
```

---

## Design decisions worth highlighting

These are choices I made deliberately, not defaults I fell into:

**Soft delete instead of hard delete.** Financial records shouldn't disappear permanently — they need to be available for audit trails and historical dashboards. `is_deleted` hides them from normal queries but admins can still see them, and the audit log stays intact.

**JSON snapshots in the audit log.** Instead of a column-level change tracking table, each audit entry stores `before_snapshot` and `after_snapshot` as JSON. This is simpler to query, easy to read, and gives you a complete picture of what changed in one row.

**`Numeric(12,2)` for money.** Floats are wrong for financial data — they accumulate rounding errors. `Numeric(12,2)` stores exact decimal values, which is what money calculations require.

**Registration always creates `viewer`.** The API doesn't accept a role on registration. This prevents a client-side bug or manipulation from granting elevated access at signup. Only admins can promote roles after the fact.

**Dashboard aggregations happen in SQL.** Trends use `date_trunc`, categories use `SUM`/`GROUP BY`, alerts compare current spend to a trailing average — all in the database. Loading thousands of rows into Python to summarize them would be wasteful and fragile.

**JWT with server-side revocation.** Stateless JWTs alone mean logout doesn't actually work — the token stays valid until it expires. I store revoked JTIs in `RevokedToken` and check them on every request. Refresh token rotation also revokes the old refresh JTI immediately, which limits exposure if a token leaks.

**`require_role` as a FastAPI dependency.** Authorization is declared at the route level — you can see exactly who can call what just by reading the router. There's no hidden middleware magic that requires digging through the call stack.

---

## Tests

```
tests/
├── test_auth.py       # Weak passwords, registration, login, refresh flow, role on register
├── test_users.py      # Viewer access restrictions, admin role management, self-targeting blocks
├── test_records.py    # Filtering, soft-delete visibility, deleted record 404 for non-admin
├── test_dashboard.py  # Summary totals, category percentages, trends, alerts, empty defaults
└── test_audit.py      # Audit log entries created on create/update/delete
```

Tests use **pytest-asyncio** with **httpx** `AsyncClient` running against the live ASGI app. One honest caveat: the default `conftest` doesn't swap in a test-only database — tests run against whatever `DATABASE_URL` is configured. For a production CI setup, you'd want a dedicated test DB with transaction rollback between tests. That's the first thing I'd fix with more time.

---

## Known limitations and honest tradeoffs

I'd rather document these clearly than have you discover them:

- **Month-over-month % in summary** — The fields exist in the response schema for analyst/admin roles, but they return `0.0` as a placeholder. The SQL query for it is straightforward; I just ran out of time to wire it up.
- **Inconsistent 403 envelope** — `require_role` raises FastAPI's `HTTPException` directly, so those 403s use FastAPI's default JSON format instead of my custom `APIException` envelope. It works, but it's not uniform.
- **Pagination on `/users`** — Computed correctly in the service, but the pagination metadata isn't always surfaced in the response envelope. Worth verifying against live responses.
- **CSV export uses creator UUID** — The `created_by` column in the CSV export is the user's UUID, not their email. Joining `User` to get the email would be cleaner.
- **Health uptime returns 0** — The liveness endpoint has an `uptime_seconds` field but it's not tracking process start time yet.

---

## What I'd improve with more time

1. Real month-over-month calculations in the summary SQL, and consistent pagination metadata on every list endpoint.
2. Unified 403/401 JSON shape for all error sources — including rate limit 429s from slowapi.
3. A proper test database fixture: containerized Postgres + Alembic applied fresh per test run.
4. CSV export joined with `User.email`, per-user rate limiting on export, and a scheduled job to prune expired revoked tokens.
5. Process start time tracking for the health uptime field, plus structured logging correlated with `X-Request-ID`.

---

*The README describes what was actually built. Where the assignment left room for interpretation (like the exact role matrix), I documented the concrete behavior rather than an idealized spec.*
