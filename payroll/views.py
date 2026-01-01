from __future__ import annotations
from calendar import monthrange
from datetime import date, timedelta
from typing import Iterable

from .models import TimeEntry


def format_timesheet(entries: Iterable[TimeEntry], start: date, end: date) -> str:
    rows = ["Timesheet", "Date        Hours  Project       Department   Earnings Code"]
    total = 0.0
    for entry in sorted(entries, key=lambda e: e.worked_date):
        if not (start <= entry.worked_date <= end):
            continue
        total += entry.hours
        rows.append(
            f"{entry.worked_date.isoformat()}  {entry.hours:>5.2f}  {entry.project or '-':<12}  {entry.department or '-':<12}  {entry.earnings_code}"
        )
    rows.append(f"Total hours: {total:.2f}")
    return "\n".join(rows)


def format_calendar(entries: Iterable[TimeEntry], year: int, month: int) -> str:
    _, last_day = monthrange(year, month)
    rows = [f"Calendar {year}-{month:02d}", "Date        Hours"]
    hours_by_day = {entry.worked_date: entry.hours for entry in entries if entry.worked_date.month == month and entry.worked_date.year == year}
    current = date(year, month, 1)
    while current.month == month:
        rows.append(f"{current.isoformat()}  {hours_by_day.get(current, 0):>5.2f}")
        current += timedelta(days=1)
    return "\n".join(rows)
