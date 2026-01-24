from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Iterable

from .audit import AuditLogger
from .exporter import export_report
from .reports import ReportRequest, build_report

SCHEDULE_FILE = Path("report_schedules.json")


@dataclass
class Schedule:
    schedule_id: str
    report_type: str
    frequency: str  # daily or weekly
    output_path: str
    last_run: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    pay_schedules: List[str] | None = None
    departments: List[str] | None = None
    employee_ids: List[str] | None = None
    group_by: str | None = None
    year: int | None = None
    quarter: int | None = None

    def is_due(self, today: date) -> bool:
        if not self.last_run:
            return True
        last_run_date = datetime.fromisoformat(self.last_run).date()
        if self.frequency == "daily":
            return last_run_date < today
        if self.frequency == "weekly":
            return last_run_date <= today - timedelta(days=7)
        return False

    def next_dates(self) -> tuple[date | None, date | None]:
        start = date.fromisoformat(self.start_date) if self.start_date else None
        end = date.fromisoformat(self.end_date) if self.end_date else None
        return start, end


class Scheduler:
    def __init__(self, schedule_path: Path = SCHEDULE_FILE, audit_logger: AuditLogger | None = None):
        self.schedule_path = schedule_path
        self.audit = audit_logger or AuditLogger()

    def _load(self) -> List[Schedule]:
        if not self.schedule_path.exists():
            return []
        with self.schedule_path.open("r", encoding="utf-8") as handle:
            records = json.load(handle)
        return [Schedule(**record) for record in records]

    def _save(self, schedules: Iterable[Schedule]) -> None:
        payload = [asdict(schedule) for schedule in schedules]
        self.schedule_path.parent.mkdir(parents=True, exist_ok=True)
        with self.schedule_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def add_schedule(self, schedule: Schedule) -> None:
        schedules = self._load()
        schedules.append(schedule)
        self._save(schedules)

    def remove_schedule(self, schedule_id: str) -> None:
        schedules = [s for s in self._load() if s.schedule_id != schedule_id]
        self._save(schedules)

    def list_schedules(self) -> List[Schedule]:
        return self._load()

    def run_due_schedules(self, payments: Iterable[Dict[str, Any]]) -> List[Path]:
        today = date.today()
        schedules = self._load()
        outputs: List[Path] = []

        for schedule in schedules:
            if not schedule.is_due(today):
                continue
            start_date, end_date = schedule.next_dates()
            request = ReportRequest(
                report_type=schedule.report_type,
                start_date=start_date,
                end_date=end_date,
                pay_schedules=schedule.pay_schedules,
                departments=schedule.departments,
                employee_ids=schedule.employee_ids,
                group_by=schedule.group_by,
                year=schedule.year,
                quarter=schedule.quarter,
            )
            rows = build_report(request, payments)
            output_path = Path(schedule.output_path)
            export_report(rows, output_path, title=schedule.report_type)
            outputs.append(output_path)
            schedule.last_run = datetime.utcnow().date().isoformat()
            self.audit.log(
                {
                    "action": "scheduled-run",
                    "report_type": schedule.report_type,
                    "output_path": str(output_path),
                    "filters": {
                        "start_date": schedule.start_date,
                        "end_date": schedule.end_date,
                        "pay_schedules": schedule.pay_schedules,
                        "departments": schedule.departments,
                        "employee_ids": schedule.employee_ids,
                        "group_by": schedule.group_by,
                        "year": schedule.year,
                        "quarter": schedule.quarter,
                    },
                }
            )

        self._save(schedules)
        return outputs
