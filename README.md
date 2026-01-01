# Payroll Platform

A modular FastAPI backend for payroll operations with domain-driven routers (auth, employees, time, payroll, payments, reporting), PostgreSQL migrations, and observability baked in.

## Stack
- API: FastAPI + Uvicorn
- DB: PostgreSQL with Alembic migrations and seed script
- Observability: Structlog JSON logs, OTLP traces/metrics, optional Sentry errors
- Containers: Docker Compose for API, Postgres, and OpenTelemetry Collector + Jaeger
- Optional static hosting: AWS S3 + CloudFront template (`infra/serverless-static`)

## Getting started
1. Copy an env file for your tier:
   ```bash
   cp .env.dev .env
   ```
2. Start the stack:
   ```bash
   docker-compose up --build
   ```
3. Run database migrations (in another shell):
   ```bash
   docker-compose exec api alembic upgrade head
   ```
4. Seed baseline data (optional):
   ```bash
   docker-compose exec api python -c "from app.db.session import SessionLocal; from app.seed.seed_data import seed;\
   from app.models import Base; from app.db.session import engine; Base.metadata.create_all(bind=engine); \
   import contextlib; from app.db.session import SessionLocal;\
   with contextlib.closing(SessionLocal()) as session: seed(session)"
   ```

API will be available at `http://localhost:8000` with endpoints for `/auth`, `/employees`, `/time`, `/payroll`, `/payments`, `/reports`, and `/health`.

## Scripts
- `scripts/backup.sh [dir]` – run a Postgres backup using `PAYROLL_DATABASE_URL`.
- `scripts/restore.sh <file>` – restore a backup.

## CI
GitHub Actions workflow runs Ruff linting and pytest using Python 3.11.
