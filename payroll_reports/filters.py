from __future__ import annotations

from datetime import date
from typing import Iterable, List, Dict, Any, Optional


PaymentRecord = Dict[str, Any]


def filter_payments(
    payments: Iterable[PaymentRecord],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    pay_schedules: Optional[List[str]] = None,
    departments: Optional[List[str]] = None,
    employee_ids: Optional[List[str]] = None,
) -> List[PaymentRecord]:
    """Filter payment records by date range, pay schedules, and departments."""

    def matches(payment: PaymentRecord) -> bool:
        if start_date and payment["pay_date"] < start_date:
            return False
        if end_date and payment["pay_date"] > end_date:
            return False
        if pay_schedules and payment.get("pay_schedule") not in pay_schedules:
            return False
        if departments and payment.get("department") not in departments:
            return False
        if employee_ids and payment.get("employee_id") not in employee_ids:
            return False
        return True

    return [payment for payment in payments if matches(payment)]
