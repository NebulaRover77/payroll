from __future__ import annotations
import csv
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import TimeEntry


CSV_HEADERS = [
    "id",
    "employee_id",
    "pay_period_id",
    "worked_date",
    "hours",
    "project",
    "department",
    "earnings_code",
    "approved",
    "notes",
]


def export_time_entries(path: Path, entries: Iterable[TimeEntry]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for entry in entries:
            writer.writerow(
                {
                    "id": entry.id,
                    "employee_id": entry.employee_id,
                    "pay_period_id": entry.pay_period_id,
                    "worked_date": entry.worked_date.isoformat(),
                    "hours": entry.hours,
                    "project": entry.project or "",
                    "department": entry.department or "",
                    "earnings_code": entry.earnings_code.value,
                    "approved": entry.approved,
                    "notes": entry.notes or "",
                }
            )


def import_time_entries(path: Path) -> list[TimeEntry]:
    entries: list[TimeEntry] = []
    with path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            entries.append(
                TimeEntry(
                    id=row["id"],
                    employee_id=row["employee_id"],
                    pay_period_id=row["pay_period_id"],
                    worked_date=date.fromisoformat(row["worked_date"]),
                    hours=float(row["hours"]),
                    project=row.get("project") or None,
                    department=row.get("department") or None,
                    earnings_code=row.get("earnings_code") or "REG",
                    approved=row.get("approved", "False") in ("True", "true", True),
                    notes=row.get("notes") or None,
                )
            )
    return entries
