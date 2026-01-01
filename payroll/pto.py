from __future__ import annotations
from datetime import date
from uuid import uuid4

from .models import EarningsCode, PTORequest, TimeEntry
from .storage import DataStore


def request_pto(store: DataStore, employee_id: str, requested_date: date, hours: float, comments: str | None = None) -> PTORequest:
    request = PTORequest(
        id=str(uuid4()),
        employee_id=employee_id,
        requested_date=requested_date,
        hours=hours,
        comments=comments,
    )
    store.add_pto_request(request)
    store.save()
    return request


def approve_pto(store: DataStore, request_id: str, approver: str, pay_period_id: str) -> TimeEntry:
    request = store.pto_requests[request_id]
    request.approved = True
    request.approver = approver
    employee = store.employees[request.employee_id]
    employee.pto_balance_hours = max(employee.pto_balance_hours - request.hours, 0)

    entry = TimeEntry(
        id=f"pto-{request.id}",
        employee_id=request.employee_id,
        pay_period_id=pay_period_id,
        worked_date=request.requested_date,
        hours=request.hours,
        earnings_code=EarningsCode.PTO,
        approved=True,
        notes=f"PTO approved by {approver}",
    )
    store.add_time_entry(entry)
    store.save()
    return entry
