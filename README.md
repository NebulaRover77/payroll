# Payroll Website

This repository contains a lightweight payroll admin panel implemented with the Python standard library and SQLite. It provides employee CRUD, compensation history, PTO accrual and usage tracking, pay run preview, and audit logging through a small WSGI app.

## Getting started

1. Ensure Python 3 is available.
2. Initialize the database and start the server:

   ```bash
   python app.py
   ```

3. Navigate to [http://localhost:8000](http://localhost:8000) in your browser.

The server will create `payroll.db` on first run and seed common pay schedules.

## Features

- Employee profiles with work/withholding states, status, default pay schedules, and compensation history.
- PTO balance management (vacation and holiday) with per-period accrual rules and usage tracking.
- Pay run preview that shows projected accruals for the selected pay date and allows applying them.
- Searchable/filterable employee list with active/terminated status and audit logging for changes.
