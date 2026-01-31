# Database Schema Reference

This document describes the relational database schema used by the FastAPI backend (Postgres via SQLAlchemy + Alembic). It reflects the current application models and migrations under `backend/app/models` and `backend/alembic`.

## Conventions
- **Primary keys**: integer `id` columns.
- **Timestamps**: `created_at` is stored in UTC (application default: `datetime.utcnow`).
- **Numeric fields**: payroll amounts use `Numeric(scale=2)` (currency-style precision).
- **Indexes**: indexes exist on primary keys and unique user emails (see details per table).

## Tables

### `users`
Authentication and authorization for API access.

| Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | Integer | No | — | Primary key. |
| `email` | String(255) | No | — | Unique, indexed. |
| `hashed_password` | String(255) | No | — | Password hash stored by the API. |
| `role` | String(50) | No | `"admin"` | Authorization role string. |
| `created_at` | DateTime | Yes | `datetime.utcnow` | Record creation timestamp. |

**Indexes**
- `ix_users_email` (unique)
- `ix_users_id`

---

### `employees`
Employee profile data, including console-specific fields for payroll operations.

| Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | Integer | No | — | Primary key. |
| `user_id` | Integer | Yes | — | Optional FK to `users.id`. |
| `first_name` | String(100) | Yes | — | Legacy/optional name fields. |
| `last_name` | String(100) | Yes | — | Legacy/optional name fields. |
| `name` | String(200) | No | — | Canonical display name (console). |
| `role` | String(200) | No | `"—"` | Console role/title. |
| `pay_type` | String(20) | No | `"salary"` | `hourly` or `salary`. |
| `rate` | Numeric(scale=2) | No | `0` | Hourly rate or salary per pay period. |
| `default_hours` | Numeric(scale=2) | No | `0` | Default hours per pay period. |
| `status` | String(20) | No | `"active"` | `active`, `on_leave`, `terminated`. |
| `tax` | String(20) | No | `"standard"` | `standard`, `low`, `high`. |
| `hire_date` | Date | Yes | — | Employee start date. |
| `annual_salary` | Numeric(scale=2) | Yes | — | Legacy salary field. |
| `created_at` | DateTime | Yes | `datetime.utcnow` | Record creation timestamp. |

**Indexes**
- `ix_employees_id`

**Relationships**
- `employees.user_id` → `users.id`

---

### `payroll_runs`
Tracks payroll periods and total amounts.

| Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | Integer | No | — | Primary key. |
| `period_start` | Date | No | — | Start date for the pay period. |
| `period_end` | Date | No | — | End date for the pay period. |
| `total_gross` | Numeric(scale=2) | No | — | Gross payroll total. |
| `status` | String(50) | No | `"draft"` | `draft`, `reviewed`, `approved`, `paid`, etc. |
| `void_reason` | String(255) | Yes | — | Optional void reason. |
| `voided_at` | DateTime | Yes | — | Timestamp when voided. |
| `created_at` | DateTime | Yes | `datetime.utcnow` | Record creation timestamp. |

**Indexes**
- `ix_payroll_runs_id`

---

### `time_entries`
Tracks employee hours worked by date.

| Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | Integer | No | — | Primary key. |
| `employee_id` | Integer | No | — | FK to `employees.id`. |
| `work_date` | Date | No | — | Date worked. |
| `hours` | Numeric(scale=2) | No | — | Hours worked for the date. |
| `project_code` | String(50) | Yes | — | Optional project or cost center code. |
| `created_at` | DateTime | Yes | `datetime.utcnow` | Record creation timestamp. |

**Indexes**
- `ix_time_entries_id`

**Relationships**
- `time_entries.employee_id` → `employees.id`

---

### `payments`
Payments issued as part of a payroll run.

| Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | Integer | No | — | Primary key. |
| `payroll_run_id` | Integer | No | — | FK to `payroll_runs.id`. |
| `employee_id` | Integer | No | — | FK to `employees.id`. |
| `amount` | Numeric(scale=2) | No | — | Payment amount. |
| `status` | String(50) | Yes | `"pending"` | `pending`, `paid`, etc. |
| `created_at` | DateTime | Yes | `datetime.utcnow` | Record creation timestamp. |

**Indexes**
- `ix_payments_id`

**Relationships**
- `payments.payroll_run_id` → `payroll_runs.id`
- `payments.employee_id` → `employees.id`

---

### `reports`
Stores generated report payloads.

| Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- |
| `id` | Integer | No | — | Primary key. |
| `name` | String(100) | No | — | Report name. |
| `payload` | JSON | No | — | Report data stored as JSON. |
| `created_at` | DateTime | Yes | `datetime.utcnow` | Record creation timestamp. |

**Indexes**
- `ix_reports_id`

---

## Relationship Summary
- `users` → `employees` (optional FK: an employee may link to a user account).
- `employees` → `time_entries` (one-to-many).
- `payroll_runs` → `payments` (one-to-many).
- `employees` → `payments` (one-to-many).

## Migrations
Initial table creation is in `backend/alembic/versions/0001_create_core_tables.py`, with later modifications (e.g., expanded employee fields and payroll run void columns) applied via subsequent Alembic migrations.
