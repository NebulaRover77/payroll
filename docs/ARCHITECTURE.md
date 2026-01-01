# Payroll Platform Architecture

## Stack choice
- **API service:** FastAPI running in a container, split into modular domain routers (auth, employees, time, payroll, payments, reporting).
- **Database:** PostgreSQL with Alembic migrations and seed script.
- **Observability:** Structlog JSON logs, OpenTelemetry traces/metrics with OTLP exporter, Sentry hook point via environment variable.
- **Deployment:** Docker Compose for local/dev, OTEL + Jaeger for tracing, optional AWS S3 + CloudFront template for static assets.

## Domain modules
- `app/domains/auth` – authentication façade and login endpoint placeholder.
- `app/domains/employees` – employee roster/read model.
- `app/domains/time_entries` – time capture.
- `app/domains/payroll` – payroll run summary.
- `app/domains/payments` – payout status projection.
- `app/domains/reporting` – reporting feed.

Routers are registered in `app/main.py` and can be expanded independently.

## Configuration per tier
Environment variables are namespaced with `PAYROLL_` and can be set in `.env.dev`, `.env.stage`, and `.env.prod`. Core settings include database URL, log level, CORS origins, Sentry DSN, and OTLP endpoint.

## Data lifecycle
- **Migrations:** run `alembic upgrade head` (env file controls the connection string).
- **Seeds:** run a small bootstrap in `app/seed/seed_data.py` against a live database session.
- **Backup/restore:** `scripts/backup.sh` and `scripts/restore.sh` wrap `pg_dump` / `psql` for DB snapshots.

## Observability & reliability
- Logs are JSON-formatted via Structlog.
- Traces/metrics are wired to OTLP (default collector at `otel-collector:4318`).
- Jaeger is available in Docker Compose for local trace visualization.
- Error monitoring: set `PAYROLL_SENTRY_DSN` to forward errors to Sentry (integration point available in settings).

## CI/CD
GitHub Actions workflow runs Ruff linting and pytest. Docker Compose can be used in CI or local dev to run the API plus PostgreSQL and the OTEL collector/Jaeger stack.
