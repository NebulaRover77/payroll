# Payroll setup wizard

This project provides a lightweight payroll company setup wizard backed by an Express API. It validates company data (including EIN, addresses, tax jurisdictions, and pay schedules), stores draft progress, and enforces completion before payroll actions are enabled.

## Getting started

```bash
npm install
npm run start
```

The server runs on http://localhost:3000 and serves the multi-step wizard UI from `/public`.

### Environment
- `ADMIN_TOKEN` (optional): token required for admin endpoints. Defaults to `changeme`.
- `PORT` (optional): HTTP port (defaults to 3000).

## API highlights
- `GET /api/setup` – fetch current setup and completion status.
- `GET /api/payroll/status` – returns whether payroll is enabled (only after setup completion).
- `GET /api/metadata` – client metadata such as states and EIN pattern.
- `POST /api/admin/progress` – (admin) save draft progress; emits an audit event.
- `POST /api/admin/setup` – (admin) validate and save the completed setup; emits an audit event.
- `GET /api/admin/audit` – (admin) view audit entries.

All admin endpoints require the `X-Admin-Token` header to match `ADMIN_TOKEN`.

## Running checks

```bash
npm test
```

The test script performs a quick schema validation and storage smoke test.
