# Finance Dashboard Backend

## Project overview

Finance Dashboard Backend is a FastAPI-based backend for a FinTech role-based financial record management system. It includes secure JWT authentication, RBAC, audit trails, and data aggregation for dashboard analytics. The architecture separates routers, services, and models to support maintainability, testability, and production readiness.

## Tech stack

| Library | Version | Purpose |
|---|---|---|
| fastapi | 0.117.0 | Web framework |
| uvicorn[standard] | 0.24.0 | ASGI server |
| SQLAlchemy[asyncio] | 2.0.20 | ORM with async DB access |
| asyncpg | 0.27.0 | PostgreSQL driver |
| alembic | 1.12.0 | migrations |
| python-jose[cryptography] | 3.2.0 | JWT implementation |
| passlib[bcrypt] | 1.7.4 | password hashing |
| pydantic | 2.8.0 | validation and settings |
| pydantic-settings | 2.2.1 | environment settings management |
| python-dotenv | 1.0.0 | .env loading |
| slowapi | 0.2.4 | rate limiting |
| pytest | 7.4.2 | testing framework |
| pytest-asyncio | 0.21.1 | async tests |
| httpx | 0.24.3 | test client |

## Architecture overview

- `app/main.py`: app factory, error handlers, routers
- `app/config.py`: pydantic settings
- `app/database.py`: async SQLAlchemy engine/session
- `app/models`: ORM models for users, records, audit, tokens
- `app/schemas`: Pydantic request/response schemas
- `app/routers`: API endpoint controllers
- `app/services`: business logic and DB operations
- `app/utils`: helpers for errors, pagination, responses
- `alembic`: DB migration tooling, includes initial schema

Services encapsulate domain logic and keep routers thin; this improves testing and reuse.

## Quick Deploy (Supabase + Render)

### 1. Supabase Setup
1. Go to [supabase.com](https://supabase.com) and create account
2. Create new project
3. Go to Settings > Database > Connection string
4. Copy the connection string (replace `[YOUR-PASSWORD]` with actual password)
5. Run migrations: In Supabase SQL Editor, paste and run:
```sql
-- Run the initial schema from alembic/versions/0001_initial.py
-- (Copy the SQL from the migration file)
```

### 2. Render Deploy
1. Go to [render.com](https://render.com) and create account
2. Create new Web Service
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables:
   - `DATABASE_URL`: Your Supabase connection string
   - `SECRET_KEY`: Generate a random string
   - `ACCESS_TOKEN_EXPIRE_MINUTES`: 30
   - `REFRESH_TOKEN_EXPIRE_MINUTES`: 43200

### 3. Seed Data
After deploy, run seed script via Render shell or API call:
```bash
python seed.py
```

### 4. Test Endpoints
- Base URL: `https://your-render-app.onrender.com`
- Login: `POST /auth/login` with viewer@zorvyn.io / Viewer@123!
- Records: `GET /records?type=income&category=Marketing`

## Seed credentials

| email | password | role |
|---|---|---|
| admin@zorvyn.io | Admin@123! | admin |
| analyst@zorvyn.io | Analyst@123! | analyst |
| viewer@zorvyn.io | Viewer@123! | viewer |

Seed script prints JWT tokens to console after run and writes `SEED_CREDENTIALS.md`.

## Role permission matrix

| Feature | Action | viewer | analyst | admin |
|---|---|---|---|---|
| Auth | Register | YES | — | — |
| Auth | Login | YES | YES | YES |
| Auth | Logout | YES | YES | YES |
| Auth | Refresh token | YES | YES | YES |
| Auth | Change own password | YES | YES | YES |
| Users | View own profile | YES | YES | YES |
| Users | Update own profile | YES | YES | YES |
| Users | List all users | NO | NO | YES |
| Users | Get user by ID | NO | NO | YES |
| Users | Change user role | NO | NO | YES |
| Users | Activate/deactivate user | NO | NO | YES |
| Records | View records (no filters: created_by, include_deleted, search; hidden notes) | YES | NO | NO |
| Records | View records (no filters: created_by, include_deleted; hidden notes) | NO | YES | NO |
| Records | View records (full access) | NO | NO | YES |
| Records | View record by ID | YES | YES | YES |
| Records | View categories | YES | YES | YES |
| Records | Create records | NO | YES | YES |
| Records | Update records | NO | NO | YES |
| Records | Soft delete records | NO | NO | YES |
| Records | Export records | NO | YES | YES |
| Dashboard | Summary (no MoM) | YES | NO | NO |
| Dashboard | Summary (full) | NO | YES | YES |
| Dashboard | Categories | YES | YES | YES |
| Dashboard | Recent (hidden notes) | YES | YES | NO |
| Dashboard | Recent (full) | NO | NO | YES |
| Dashboard | Trends | NO | YES | YES |
| Dashboard | Alerts | NO | YES | YES |
| Audit | Full audit log | NO | NO | YES |

## API reference

(This section should be expanded with all endpoint docs; for brevity, only key endpoints are listed.)

- `POST /auth/register`: no auth, role viewer, register user.
- `POST /auth/login`: no auth, any role, receive JWTs.
- `POST /auth/refresh`: no auth, any role, rotate refresh token.
- `POST /auth/logout`: auth required, any role, revoke current token.
- `POST /auth/change-password`: auth required, any role.
- `GET /users/me`: auth required, any role.
- `PATCH /users/me`: auth required, any role.
- `GET /users`: auth admin.
- `GET /records`: auth any.
- `POST /records`: auth analyst/admin.
- `GET /records/export`: auth analyst/admin.
- `GET /dashboard/summary`: auth analyst/admin.
- `GET /audit-log`: auth admin.
- `GET /health`: open.
- `GET /health/ready`: open.

## Example requests

1. Register:
```
curl -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' -d '{"email":"new@example.com","password":"Strong1!","full_name":"New User"}'
```
2. Login:
```
curl -X POST http://localhost:8000/auth/login -H 'Content-Type: application/json' -d '{"email":"admin@zorvyn.io","password":"Admin@123!"}'
```
3. Create record (analyst/admin):
```
curl -X POST http://localhost:8000/records -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' -d '{"amount": 415000, "type":"income", "category":"Consulting", "date":"2026-03-15"}'
```
4. Get dashboard summary:
```
curl -X GET 'http://localhost:8000/dashboard/summary?period=current_month' -H 'Authorization: Bearer <token>'
```
5. Export CSV:
```
curl -X GET 'http://localhost:8000/records/export' -H 'Authorization: Bearer <token>' -o records.csv
```

## Design decisions

1. Soft delete uses `is_deleted` to preserve data and maintain audit history.
2. Audit log records `before_snapshot` and `after_snapshot` for traceability and compliance.
3. Numeric(12,2) for amounts avoids float precision issues in money calculations.
4. Register endpoint always assigns `viewer` role to prevent privilege escalation.
5. Dashboard uses DB-level aggregation functions to optimize performance and avoid Python memory overhead.

## Assumptions

- The PostgreSQL URL uses asyncpg and is configured via `.env`.
- Refresh token includes `type":"refresh"` claim for differentiation.
- `get_current_user` validates token and active status.
- Pagination defaults to page=1 and limit=20.
- Rate limits assume per-IP and per-user by slowapi.

## What would be improved with more time

1. Add full integration test coverage with database fixtures and real JWT tokens.
2. Add periodic cleanup job for old revoked tokens.
3. Implement more robust password reset and email verification flows.
4. Add OAuth2 / 3rd-party provider support.
5. Add Docker compose and CI pipeline with db migration checks.
