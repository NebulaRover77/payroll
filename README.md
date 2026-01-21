# Payroll

A playground/monorepo for a payroll platform: a FastAPI backend, an Express-based setup wizard, and a lightweight static “console” UI. Supporting docs cover security, feature requirements, and architecture.

## Docs (start here)
- Security: `docs/SECURITY_DESIGN.md`
- Feature requirements (paystubs/W-2, delivery, compliance): `docs/payroll_features.md`
- Payroll run design: `docs/payroll_run_design.md`
- Architecture notes: `docs/ARCHITECTURE.md`
- Feature plan: `FEATURE_PLAN.md`

---

## Quickstart

**One-liner (API + DB + OTEL + wizard + console):**

```bash
docker compose up --build
```

After the stack is up, run migrations in another shell:

```bash
docker compose exec api alembic upgrade head
```

### Seed an initial admin login
Create the first username/password after migrations so you can authenticate against the API:

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.test","password":"supersafepassword","role":"admin"}'
```

The `/users` endpoint stores the password using a built-in hash and enforces a minimum length of 8 characters; the example above seeds an `admin`-role account you can reuse for initial access.

### Backend API (FastAPI + Postgres + migrations)
Runs the API, Postgres, and observability tooling via Docker Compose (uses `docker-compose.yml`).

API is typically at:
- http://localhost:8000
Health check:
- http://localhost:8000/health

Notes:
- Backup/restore helpers: `scripts/backup.sh` and `scripts/restore.sh` (use `PAYROLL_DATABASE_URL`).

### Payroll Setup Wizard (Express + static UI)
Runs the multi-step setup wizard served from `public/`.

The Docker Compose stack starts this service automatically (port `3000`). To run it in isolation or stream logs:

```bash
docker compose up wizard
# or
docker compose logs -f wizard
```

Environment (configured via Compose):
- `ADMIN_TOKEN` (optional): admin token for protected endpoints (default: `changeme`)
- `PORT` (optional): server port (default: `3000`)

API highlights:
- `GET /api/setup` — fetch current setup + completion status
- `GET /api/payroll/status` — whether payroll actions are enabled (post-setup)
- `GET /api/metadata` — client metadata (states, EIN pattern)
- `POST /api/admin/progress` — save draft progress (admin; emits audit event)
- `POST /api/admin/setup` — validate + save completed setup (admin; emits audit event)
- `GET /api/admin/audit` — view audit entries (admin)

Admin endpoints require `X-Admin-Token: <ADMIN_TOKEN>`.

### Static Console (Nginx container)
A simple static UI served by Nginx (files live in `frontend/console/`).

Console:
- http://localhost:8080

---

## Repo layout (high level)

- `backend/` — FastAPI app code (routers, models, config, observability)
- `docker-compose.yml` — compose stack for API, DB, observability, wizard, and console
- `frontend/console/` — static console UI assets + Dockerfile
- `src/` + `public/` + `package.json` — Express setup wizard
- `docs/` — security/architecture/feature design docs
- `scripts/` — backup/restore + misc utilities

## CI
GitHub Actions runs Python lint/tests for the backend (see `.github/workflows/ci.yml`).
