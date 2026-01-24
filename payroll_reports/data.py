from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


Store = Dict[str, Any]
EmployeeRecord = Dict[str, Any]
PaymentRecord = Dict[str, Any]
PayTypeRecord = Dict[str, Any]


@dataclass(frozen=True)
class StoreData:
    employees: List[EmployeeRecord]
    pay_types: List[PayTypeRecord]
    payments: List[PaymentRecord]


def load_store(store_path: Path) -> Store:
    if not store_path.exists():
        raise FileNotFoundError(f"Store data not found at {store_path}")
    with store_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        date_part = value.split("T")[0]
        try:
            parsed = date.fromisoformat(date_part)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None
    return parsed


def _index_pay_types(pay_types: Iterable[PayTypeRecord]) -> Dict[str, str]:
    return {pay_type.get("id"): pay_type.get("name", pay_type.get("id", "")) for pay_type in pay_types}


def _sum_hours(pay_lines: Dict[str, Any]) -> float:
    total = 0.0
    for details in pay_lines.values():
        total += float(details.get("hours") or 0.0)
    return round(total, 2)


def build_payments(store: Store) -> List[PaymentRecord]:
    history = [entry for entry in store.get("payroll_history", []) if entry.get("entry_type") == "check"]
    employees = {employee.get("id"): employee for employee in store.get("employees", [])}
    pay_type_names = _index_pay_types(store.get("pay_types", []))
    payments: List[PaymentRecord] = []

    for entry in history:
        check_date = _parse_iso_date(entry.get("check_date"))
        if not check_date:
            continue
        employee_id = entry.get("employee_id")
        employee = employees.get(employee_id, {})
        pay_lines = entry.get("pay_lines", {}) or {}
        earnings: List[Dict[str, Any]] = []
        for pay_type_id, details in pay_lines.items():
            earnings.append(
                {
                    "type": pay_type_names.get(pay_type_id, pay_type_id),
                    "hours": float(details.get("hours") or 0.0),
                    "amount": float(details.get("amount") or 0.0),
                }
            )

        gross = float(entry.get("gross") or 0.0)
        employee_taxes = {
            "fit": float(entry.get("fit") or 0.0),
            "ss": float(entry.get("employee_ss") or 0.0),
            "medicare": float(entry.get("employee_medicare") or 0.0),
        }
        employer_taxes = {
            "fit": 0.0,
            "ss": float(entry.get("employer_ss") or 0.0),
            "medicare": float(entry.get("employer_medicare") or 0.0),
            "futa": float(entry.get("futa") or 0.0),
            "suta": float(entry.get("suta") or 0.0),
        }

        payments.append(
            {
                "employee_id": employee_id,
                "employee_name": employee.get("name") or employee_id,
                "pay_date": check_date,
                "gross_pay": gross,
                "net_pay": float(entry.get("net") or 0.0),
                "taxes": float(entry.get("taxes") or 0.0),
                "deductions": 0.0,
                "hours": _sum_hours(pay_lines),
                "department": employee.get("department", ""),
                "project": employee.get("project", ""),
                "pay_schedule": employee.get("pay_schedule", ""),
                "earnings": earnings,
                "deductions_detail": [],
                "contributions_detail": [],
                "employee_taxes": employee_taxes,
                "employer_taxes": employer_taxes,
                "taxable_wages": {
                    "fit": gross,
                    "ss": gross,
                    "medicare": gross,
                    "futa": gross,
                    "suta": gross,
                },
                "allocations": [],
            }
        )
    return payments


def load_store_data(store_path: Path) -> StoreData:
    store = load_store(store_path)
    return StoreData(
        employees=list(store.get("employees", [])),
        pay_types=list(store.get("pay_types", [])),
        payments=build_payments(store),
    )
