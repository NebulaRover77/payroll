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

### 1) Backend API (FastAPI + Postgres + migrations)
Runs the API, Postgres, and observability tooling via Docker Compose (uses `docker-compose.yml`).

```bash
docker compose up --build
```

In another shell, run migrations:

```bash
docker compose exec api alembic upgrade head
```

API is typically at:
- http://localhost:8000  
Health check:
- http://localhost:8000/health

Notes:
- Backup/restore helpers: `scripts/backup.sh` and `scripts/restore.sh` (use `PAYROLL_DATABASE_URL`).

---

### 2) Payroll Setup Wizard (Express + static UI)
Runs the multi-step setup wizard served from `public/`.

```bash
npm install
npm run start
```

Via Docker Compose (builds `Dockerfile.wizard` and binds port 3000):

```bash
docker compose up --build wizard
```

Wizard server:
- http://localhost:3000

Environment:
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

Run checks:
```bash
npm test
```

---

### 3) Static Console (Nginx container)
A simple static UI served by Nginx (files live in `frontend/console/`).

```bash
docker compose -f compose.console.yaml up --build
```

Console:
- http://localhost:8080

---

## Repo layout (high level)

- `backend/` — FastAPI app code (routers, models, config, observability)
- `docker-compose.yml` — backend compose stack (API + Postgres + OTEL tooling)
- `frontend/console/` — static console UI assets + Dockerfile
- `compose.console.yaml` — compose file for the static console
- `src/` + `public/` + `package.json` — Express setup wizard
- `docs/` — security/architecture/feature design docs
- `scripts/` — backup/restore + misc utilities

---

## CI
GitHub Actions runs Python lint/tests for the backend (see `.github/workflows/ci.yml`).
