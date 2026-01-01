# Payroll Website

This repository provides a lightweight payroll toolkit with time entry, overtime classification, PTO approvals, and CSV import/export helpers. The code is organized as a Python package under `payroll/` and includes a CLI for self-service and admin operations.

## Features
- **Time entry model** with project/department tags, earnings codes, approval flag, and links to employees and pay periods.
- **Overtime engine** that supports weekly thresholds (default 40 hours) and state-style daily overtime/double-time rules.
- **PTO requests and approvals** that automatically convert to PTO time entries and reduce PTO balances.
- **Calendar and timesheet views** to quickly review hours.
- **CSV import/export** to bulk load time data.

## Quick start
1. Install Python 3.11+ and run commands from the repo root.
2. Use the CLI to seed data and manage entries (data is stored in `data/store.json`).

```bash
# Add an employee and pay period
python -m payroll.cli add-employee "Jane Worker" "Engineering" --pto 24
python -m payroll.cli add-pay-period 2024-07-01 2024-07-15

# Self-service time entry
python -m payroll.cli add-time <employee_id> <pay_period_id> 2024-07-01 8 --project Alpha --department Engineering

# Manager approval and overtime classification
python -m payroll.cli approve-time <entry_id>
python -m payroll.cli classify <employee_id> 2024-07-01 --weekly-threshold 40 --state CA

# PTO workflow
python -m payroll.cli request-pto <employee_id> 2024-07-05 8 --comments "Vacation"
python -m payroll.cli approve-pto <pto_request_id> <approver_id> <pay_period_id>

# Views and data export
python -m payroll.cli timesheet <employee_id> 2024-07-01
python -m payroll.cli calendar <employee_id> 2024 7
python -m payroll.cli export times.csv --employee <employee_id>
python -m payroll.cli import times.csv
```

The CLI commands are organized for both **self-service** (adding time, requesting PTO) and **admin/manager** flows (approving time, running overtime classification, approving PTO, exporting data).
