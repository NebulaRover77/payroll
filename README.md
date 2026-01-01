# Payroll

This repository contains payroll-related services. Depending on what you’re running locally, use one of the setups below.

## Security Architecture

See docs/SECURITY_DESIGN.md for the authentication, MFA, RBAC, encryption, audit logging, and session control plan (SOC 2 Type II–oriented).

## Feature Overview

- Generate paystub PDFs per payroll run with earning codes, taxes, deductions, PTO balances, and YTD totals.
- Provide an employee portal for secure, logged access to historical paystubs.
- Implement W-2 generation using stored annual totals with admin downloads and employee self-service access.

See docs/payroll_features.md for detailed requirements covering document content, delivery, security, and compliance expectations.

---

## Option A: Payroll Platform (FastAPI)

A modular FastAPI backend for payroll operations with domain-driven routers (auth, employees, time, payroll, payments, reporting), PostgreSQL migrations, and observability baked in.

## Stack
- API: FastAPI + Uvicorn
- DB: PostgreSQL with Alembic migrations and seed script
- Observability: Structlog JSON logs, OTLP traces/metrics, optional Sentry errors
- Containers: Docker Compose for API, Postgres, and OpenTelemetry Collector + Jaeger
- Optional static hosting: AWS S3 + CloudFront template (infra/serverless-static)

## Getting started
1. Copy an env file for your tier:
   ~~~bash
   cp .env.dev .env
   ~~~
2. Start the stack:
   ~~~bash
   docker-compose up --build
   ~~~
3. Run database migrations (in another shell):
   ~~~bash
   docker-compose exec api alembic upgrade head
   ~~~
4. Seed baseline data (optional):
   ~~~bash
   docker-compose exec api python -c "from app.seed.seed_data import seed; import contextlib; from app.db.session import SessionLocal; with contextlib.closing(SessionLocal()) as session: seed(session)"
   ~~~

API will be available at http://localhost:8000 with endpoints for /auth, /employees, /time, /payroll, /payments, /reports, and /health.

## Scripts
- scripts/backup.sh [dir] – run a Postgres backup using PAYROLL_DATABASE_URL.
- scripts/restore.sh <file> – restore a backup.

## CI
GitHub Actions workflow runs Ruff linting and pytest using Python 3.11.

---

## Option B: Payroll Setup Wizard (Express)

This project provides a lightweight payroll company setup wizard backed by an Express API. It validates company data (including EIN, addresses, tax jurisdictions, and pay schedules), stores draft progress, and enforces completion before payroll actions are enabled.

## Getting started
~~~bash
npm install
npm run start
~~~

The server runs on http://localhost:3000 and serves the multi-step wizard UI from /public.

### Environment
- ADMIN_TOKEN (optional): token required for admin endpoints. Defaults to changeme.
- PORT (optional): HTTP port (defaults to 3000).

## API highlights
- GET /api/setup – fetch current setup and completion status.
- GET /api/payroll/status – returns whether payroll is enabled (only after setup completion).
- GET /api/metadata – client metadata such as states and EIN pattern.
- POST /api/admin/progress – (admin) save draft progress; emits an audit event.
- POST /api/admin/setup – (admin) validate and save the completed setup; emits an audit event.
- GET /api/admin/audit – (admin) view audit entries.

All admin endpoints require the X-Admin-Token header to match ADMIN_TOKEN.

## Running checks
~~~bash
npm test
~~~

The test script performs a quick schema validation and storage smoke test.
