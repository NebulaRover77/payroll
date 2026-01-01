from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Any, Iterable

from .filters import filter_payments


@dataclass
class ReportRequest:
    report_type: str
    start_date: date | None = None
    end_date: date | None = None
    pay_schedules: List[str] | None = None
    departments: List[str] | None = None


ReportRow = Dict[str, Any]


def payroll_register(payments: Iterable[ReportRow]) -> List[ReportRow]:
    rows: List[ReportRow] = []
    for payment in payments:
        rows.append(
            {
                "employee_id": payment["employee_id"],
                "pay_date": payment["pay_date"],
                "department": payment["department"],
                "project": payment.get("project"),
                "gross_pay": payment["gross_pay"],
                "taxes": payment["taxes"],
                "deductions": payment["deductions"],
                "net_pay": payment["net_pay"],
            }
        )
    return rows


def payment_detail(payments: Iterable[ReportRow]) -> List[ReportRow]:
    rows: List[ReportRow] = []
    for payment in payments:
        rows.append(
            {
                **payment,
                "allocations": payment.get("allocations", []),
            }
        )
    return rows


def deductions_and_taxes_summary(payments: Iterable[ReportRow]) -> List[ReportRow]:
    totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {"taxes": 0.0, "deductions": 0.0})
    for payment in payments:
        employee_totals = totals[payment["employee_id"]]
        employee_totals["taxes"] += payment["taxes"]
        employee_totals["deductions"] += payment["deductions"]

    rows: List[ReportRow] = []
    for employee_id, values in totals.items():
        rows.append(
            {
                "employee_id": employee_id,
                "taxes": round(values["taxes"], 2),
                "deductions": round(values["deductions"], 2),
            }
        )
    return rows


def labor_distribution(payments: Iterable[ReportRow]) -> List[ReportRow]:
    buckets: Dict[str, Dict[str, float]] = defaultdict(lambda: {"hours": 0.0, "wages": 0.0})
    for payment in payments:
        for allocation in payment.get("allocations", []):
            key = f"{allocation['department']}|{allocation['project']}"
            bucket = buckets[key]
            bucket["hours"] += allocation.get("hours", 0.0)
            bucket["wages"] += allocation.get("wages", 0.0)

    rows: List[ReportRow] = []
    for key, totals in buckets.items():
        department, project = key.split("|")
        rows.append(
            {
                "department": department,
                "project": project,
                "hours": round(totals["hours"], 2),
                "wages": round(totals["wages"], 2),
            }
        )
    return rows


REPORT_BUILDERS = {
    "payroll-register": payroll_register,
    "payment-detail": payment_detail,
    "deductions-taxes-summary": deductions_and_taxes_summary,
    "labor-distribution": labor_distribution,
}


def build_report(request: ReportRequest, payments: Iterable[ReportRow]) -> List[ReportRow]:
    filtered = filter_payments(
        payments,
        start_date=request.start_date,
        end_date=request.end_date,
        pay_schedules=request.pay_schedules,
        departments=request.departments,
    )
    try:
        builder = REPORT_BUILDERS[request.report_type]
    except KeyError as exc:
        raise ValueError(f"Unknown report type: {request.report_type}") from exc
    return builder(filtered)
