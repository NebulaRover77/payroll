from __future__ import annotations
from datetime import date
from typing import Iterable, List

from .models import EarningsCode, TimeEntry
from .overtime import OvertimeEngine, week_bounds
from .storage import DataStore


def create_time_entry(
    store: DataStore,
    *,
    entry_id: str,
    employee_id: str,
    pay_period_id: str,
    worked_date: date,
    hours: float,
    project: str | None = None,
    department: str | None = None,
    notes: str | None = None,
) -> TimeEntry:
    entry = TimeEntry(
        id=entry_id,
        employee_id=employee_id,
        pay_period_id=pay_period_id,
        worked_date=worked_date,
        hours=hours,
        project=project,
        department=department,
        notes=notes,
    )
    store.add_time_entry(entry)
    store.save()
    return entry


def approve_time_entry(store: DataStore, entry_id: str) -> TimeEntry:
    entry = store.time_entries[entry_id]
    entry.approved = True
    store.save()
    return entry


def classify_hours(
    store: DataStore,
    engine: OvertimeEngine,
    employee_id: str,
    anchor_date: date,
) -> List[TimeEntry]:
    start, end = week_bounds(anchor_date)
    entries = [e for e in store.time_entries.values() if e.employee_id == employee_id and start <= e.worked_date <= end]
    overtime_result = engine.classify_time_entries(employee_id, start, end, entries)

    # Apply earnings code classification
    for classification in overtime_result.days:
        for entry in entries:
            if entry.worked_date == classification.worked_date:
                entry.earnings_code = EarningsCode.REGULAR
                if classification.bucket.overtime_hours > 0:
                    entry.earnings_code = EarningsCode.OVERTIME
                if classification.bucket.doubletime_hours > 0:
                    entry.earnings_code = EarningsCode.DOUBLE_TIME
    store.save()
    return entries


def pending_entries(store: DataStore, employee_id: str | None = None) -> Iterable[TimeEntry]:
    for entry in store.find_entries(employee_id):
        if not entry.approved:
            yield entry
