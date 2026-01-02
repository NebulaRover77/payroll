from __future__ import annotations
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from .models import Employee, PTORequest, PayPeriod, TimeEntry


class DataStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.employees: Dict[str, Employee] = {}
        self.pay_periods: Dict[str, PayPeriod] = {}
        self.time_entries: Dict[str, TimeEntry] = {}
        self.pto_requests: Dict[str, PTORequest] = {}
        if path.exists():
            self.load()

    def load(self) -> None:
        content = json.loads(self.path.read_text())
        self.employees = {e["id"]: Employee(**e) for e in content.get("employees", [])}
        self.pay_periods = {p["id"]: PayPeriod(**p) for p in content.get("pay_periods", [])}
        self.time_entries = {t["id"]: self._deserialize_time_entry(t) for t in content.get("time_entries", [])}
        self.pto_requests = {r["id"]: self._deserialize_pto_request(r) for r in content.get("pto_requests", [])}

    def save(self) -> None:
        payload = {
            "employees": [asdict(e) for e in self.employees.values()],
            "pay_periods": [asdict(p) for p in self.pay_periods.values()],
            "time_entries": [self._serialize_time_entry(t) for t in self.time_entries.values()],
            "pto_requests": [self._serialize_pto_request(r) for r in self.pto_requests.values()],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, default=self._date_serializer, indent=2))

    def add_employee(self, employee: Employee) -> None:
        self.employees[employee.id] = employee

    def add_pay_period(self, pay_period: PayPeriod) -> None:
        self.pay_periods[pay_period.id] = pay_period

    def add_time_entry(self, entry: TimeEntry) -> None:
        self.time_entries[entry.id] = entry

    def add_pto_request(self, request: PTORequest) -> None:
        self.pto_requests[request.id] = request

    def find_entries(self, employee_id: Optional[str] = None) -> List[TimeEntry]:
        entries = list(self.time_entries.values())
        if employee_id:
            entries = [e for e in entries if e.employee_id == employee_id]
        return sorted(entries, key=lambda e: e.worked_date)

    def list_employees(self) -> List[Employee]:
        """Return employees ordered by display name."""

        return sorted(self.employees.values(), key=lambda e: e.name.lower())

    @staticmethod
    def _date_serializer(value):
        if isinstance(value, date):
            return value.isoformat()
        raise TypeError(f"Type {type(value)} not serializable")

    @staticmethod
    def _parse_date(value: str) -> date:
        return date.fromisoformat(value)

    def _serialize_time_entry(self, entry: TimeEntry) -> dict:
        payload = asdict(entry)
        payload["worked_date"] = entry.worked_date.isoformat()
        payload["earnings_code"] = entry.earnings_code.value
        return payload

    def _serialize_pto_request(self, request: PTORequest) -> dict:
        payload = asdict(request)
        payload["requested_date"] = request.requested_date.isoformat()
        return payload

    def _deserialize_time_entry(self, data: dict) -> TimeEntry:
        data["worked_date"] = self._parse_date(data["worked_date"])
        data["earnings_code"] = data.get("earnings_code")
        return TimeEntry(**data)

    def _deserialize_pto_request(self, data: dict) -> PTORequest:
        data["requested_date"] = self._parse_date(data["requested_date"])
        return PTORequest(**data)
