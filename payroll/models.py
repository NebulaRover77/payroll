from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional


class EarningsCode(str, Enum):
    REGULAR = "REG"
    OVERTIME = "OT"
    DOUBLE_TIME = "DT"
    PTO = "PTO"


@dataclass
class Employee:
    id: str
    name: str
    department: str
    pto_balance_hours: float = 0.0


@dataclass
class PayPeriod:
    id: str
    start: date
    end: date


@dataclass
class TimeEntry:
    id: str
    employee_id: str
    pay_period_id: str
    worked_date: date
    hours: float
    project: Optional[str] = None
    department: Optional[str] = None
    earnings_code: EarningsCode = EarningsCode.REGULAR
    approved: bool = False
    notes: Optional[str] = None


@dataclass
class PTORequest:
    id: str
    employee_id: str
    requested_date: date
    hours: float
    approved: bool = False
    approver: Optional[str] = None
    comments: Optional[str] = None


@dataclass
class Approval:
    time_entry_id: str
    approver: str
    approved_on: date


@dataclass
class OvertimeBucket:
    regular_hours: float = 0.0
    overtime_hours: float = 0.0
    doubletime_hours: float = 0.0


@dataclass
class DayClassification:
    worked_date: date
    total_hours: float
    bucket: OvertimeBucket


@dataclass
class WeeklyOvertimeResult:
    employee_id: str
    week_start: date
    week_end: date
    days: List[DayClassification] = field(default_factory=list)
    total_regular_hours: float = 0.0
    total_ot_hours: float = 0.0
    total_dt_hours: float = 0.0

    def add_day(self, classification: DayClassification) -> None:
        self.days.append(classification)
        self.total_regular_hours += classification.bucket.regular_hours
        self.total_ot_hours += classification.bucket.overtime_hours
        self.total_dt_hours += classification.bucket.doubletime_hours
