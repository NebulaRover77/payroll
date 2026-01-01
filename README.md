# Payroll Reporting Toolkit

This repository provides a lightweight payroll reporting utility with sample data. It can produce payroll register, payment detail, deductions/taxes summary, and labor distribution reports with date, pay schedule, and department filters. Reports export to CSV or PDF, can be scheduled, and every access is captured in an audit log.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commands

Run a report immediately (prints JSON if no output file is provided):

```bash
python -m payroll_reports.cli run-report \
  --report payroll-register \
  --start-date 2024-07-01 \
  --end-date 2024-07-31 \
  --pay-schedule Biweekly \
  --department Engineering \
  --output outputs/payroll-register.csv
```

Add a scheduled report that will be generated on the next `schedule-run` and then daily afterward:

```bash
python -m payroll_reports.cli schedule-add \
  --id july-payroll \
  --report deductions-taxes-summary \
  --frequency daily \
  --start-date 2024-07-01 \
  --end-date 2024-07-31 \
  --output outputs/deductions.pdf
```

Run any schedules that are due based on their last run date:

```bash
python -m payroll_reports.cli schedule-run
```

List and remove schedules:

```bash
python -m payroll_reports.cli schedule-list
python -m payroll_reports.cli schedule-remove --id july-payroll
```

Show the audit log of manual and scheduled report executions:

```bash
python -m payroll_reports.cli audit
```
