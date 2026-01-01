from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, Iterable, List, Tuple

from .models import DayClassification, OvertimeBucket, TimeEntry, WeeklyOvertimeResult


@dataclass
class OvertimeRule:
    """Base overtime rule interface."""

    def classify(self, daily_hours: float) -> OvertimeBucket:
        raise NotImplementedError


@dataclass
class WeeklyThresholdRule(OvertimeRule):
    threshold: float = 40.0
    double_time_threshold: float = 0.0

    def classify_week(self, total_hours: float) -> Tuple[float, float, float]:
        regular = min(total_hours, self.threshold)
        overtime = 0.0
        double_time = 0.0
        remaining = total_hours - regular
        if remaining > 0:
            overtime = min(remaining, self.double_time_threshold or remaining)
            remaining -= overtime
        if remaining > 0:
            double_time += remaining
        return regular, overtime, double_time

    def classify(self, daily_hours: float) -> OvertimeBucket:  # pragma: no cover - unused
        return OvertimeBucket(regular_hours=daily_hours)


@dataclass
class DailyStateRule(OvertimeRule):
    state: str
    daily_threshold: float = 8.0
    double_time_threshold: float = 12.0

    def classify(self, daily_hours: float) -> OvertimeBucket:
        regular = min(daily_hours, self.daily_threshold)
        remaining = daily_hours - regular
        overtime = 0.0
        double_time = 0.0
        if remaining > 0:
            overtime = min(remaining, max(self.double_time_threshold - self.daily_threshold, 0))
            remaining -= overtime
        if remaining > 0:
            double_time = remaining
        return OvertimeBucket(regular_hours=regular, overtime_hours=overtime, doubletime_hours=double_time)


class OvertimeEngine:
    def __init__(self, weekly_rule: WeeklyThresholdRule, state_rule: DailyStateRule | None = None) -> None:
        self.weekly_rule = weekly_rule
        self.state_rule = state_rule

    def classify_time_entries(self, employee_id: str, start: date, end: date, entries: Iterable[TimeEntry]) -> WeeklyOvertimeResult:
        # Group by day
        daily_hours: Dict[date, float] = defaultdict(float)
        for entry in entries:
            if entry.employee_id != employee_id or not (start <= entry.worked_date <= end):
                continue
            daily_hours[entry.worked_date] += entry.hours

        result = WeeklyOvertimeResult(employee_id=employee_id, week_start=start, week_end=end)

        # Daily classification (state specific)
        daily_buckets: List[DayClassification] = []
        for day, hours in sorted(daily_hours.items()):
            if self.state_rule:
                bucket = self.state_rule.classify(hours)
            else:
                bucket = OvertimeBucket(regular_hours=hours)
            daily_buckets.append(DayClassification(worked_date=day, total_hours=hours, bucket=bucket))

        # Weekly adjustment
        total_hours = sum(d.total_hours for d in daily_buckets)
        regular_total, ot_total, dt_total = self.weekly_rule.classify_week(total_hours)

        # Reconcile weekly totals by scaling regular hours down if needed
        allocated_regular = 0.0
        for classification in daily_buckets:
            # assign initial classification
            bucket = classification.bucket
            # Adjust based on weekly threshold
            if allocated_regular + bucket.regular_hours <= regular_total:
                allocated_regular += bucket.regular_hours
            else:
                over_regular = allocated_regular + bucket.regular_hours - regular_total
                bucket.regular_hours -= over_regular
                bucket.overtime_hours += over_regular
                allocated_regular = regular_total
            result.add_day(classification)

        # distribute overtime that exceeds daily calculations
        actual_ot = result.total_ot_hours + result.total_dt_hours
        weekly_extra_ot = (ot_total + dt_total) - actual_ot
        if weekly_extra_ot > 0 and result.days:
            per_day_extra = weekly_extra_ot / len(result.days)
            for classification in result.days:
                classification.bucket.overtime_hours += per_day_extra
                result.total_ot_hours += per_day_extra

        return result


def week_bounds(anchor: date) -> Tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())
    end = start + timedelta(days=6)
    return start, end
