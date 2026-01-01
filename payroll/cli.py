from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path
from uuid import uuid4

from .csv_io import export_time_entries, import_time_entries
from .models import Employee, PayPeriod
from .overtime import DailyStateRule, OvertimeEngine, WeeklyThresholdRule, week_bounds
from .pto import approve_pto, request_pto
from .storage import DataStore
from .time_tracking import approve_time_entry, classify_hours, create_time_entry, pending_entries
from .views import format_calendar, format_timesheet


DEFAULT_DATA_PATH = Path("data/store.json")


def store_from_args(args: argparse.Namespace) -> DataStore:
    return DataStore(DEFAULT_DATA_PATH)


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def cmd_add_employee(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    employee = Employee(id=args.id or str(uuid4()), name=args.name, department=args.department, pto_balance_hours=args.pto)
    store.add_employee(employee)
    store.save()
    print(f"Added employee {employee.id} ({employee.name})")


def cmd_add_pay_period(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    pay_period = PayPeriod(id=args.id or str(uuid4()), start=parse_date(args.start), end=parse_date(args.end))
    store.add_pay_period(pay_period)
    store.save()
    print(f"Added pay period {pay_period.id} {pay_period.start} - {pay_period.end}")


def cmd_add_time(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    entry = create_time_entry(
        store,
        entry_id=args.id or str(uuid4()),
        employee_id=args.employee,
        pay_period_id=args.pay_period,
        worked_date=parse_date(args.date),
        hours=args.hours,
        project=args.project,
        department=args.department,
        notes=args.notes,
    )
    print(f"Created time entry {entry.id} for {entry.hours} hours on {entry.worked_date}")


def cmd_approve_time(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    entry = approve_time_entry(store, args.id)
    print(f"Approved entry {entry.id}")


def cmd_classify(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    weekly_rule = WeeklyThresholdRule(threshold=args.weekly_threshold, double_time_threshold=args.double_time)
    state_rule = DailyStateRule(state=args.state, daily_threshold=args.daily_threshold, double_time_threshold=args.daily_double)
    engine = OvertimeEngine(weekly_rule=weekly_rule, state_rule=state_rule)
    entries = classify_hours(store, engine, args.employee, parse_date(args.anchor))
    print(f"Classified {len(entries)} entries")


def cmd_request_pto(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    request = request_pto(store, args.employee, parse_date(args.date), args.hours, args.comments)
    print(f"Requested PTO {request.id} for {request.hours} hours")


def cmd_approve_pto(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    entry = approve_pto(store, args.id, args.approver, args.pay_period)
    print(f"Approved PTO as entry {entry.id}")


def cmd_timesheet(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    start, end = week_bounds(parse_date(args.anchor))
    entries = store.find_entries(args.employee)
    print(format_timesheet(entries, start, end))


def cmd_calendar(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    entries = store.find_entries(args.employee)
    print(format_calendar(entries, args.year, args.month))


def cmd_export(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    path = Path(args.path)
    export_time_entries(path, store.find_entries(args.employee))
    print(f"Exported entries to {path}")


def cmd_import(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    path = Path(args.path)
    entries = import_time_entries(path)
    for entry in entries:
        store.add_time_entry(entry)
    store.save()
    print(f"Imported {len(entries)} entries from {path}")


def cmd_pending(args: argparse.Namespace) -> None:
    store = store_from_args(args)
    for entry in pending_entries(store, args.employee):
        print(f"{entry.id} {entry.employee_id} {entry.worked_date} {entry.hours}h project={entry.project} approved={entry.approved}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Payroll time tracking CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    employee = sub.add_parser("add-employee", help="Add an employee")
    employee.add_argument("name")
    employee.add_argument("department")
    employee.add_argument("--id")
    employee.add_argument("--pto", type=float, default=0.0, help="Starting PTO balance in hours")
    employee.set_defaults(func=cmd_add_employee)

    pay_period = sub.add_parser("add-pay-period", help="Add a pay period")
    pay_period.add_argument("start")
    pay_period.add_argument("end")
    pay_period.add_argument("--id")
    pay_period.set_defaults(func=cmd_add_pay_period)

    add_time = sub.add_parser("add-time", help="Self-service time entry")
    add_time.add_argument("employee")
    add_time.add_argument("pay_period")
    add_time.add_argument("date")
    add_time.add_argument("hours", type=float)
    add_time.add_argument("--project")
    add_time.add_argument("--department")
    add_time.add_argument("--notes")
    add_time.add_argument("--id")
    add_time.set_defaults(func=cmd_add_time)

    approve_time = sub.add_parser("approve-time", help="Manager approval of time entry")
    approve_time.add_argument("id")
    approve_time.set_defaults(func=cmd_approve_time)

    classify = sub.add_parser("classify", help="Run overtime classification")
    classify.add_argument("employee")
    classify.add_argument("anchor", help="Any date in the week to classify")
    classify.add_argument("--weekly-threshold", type=float, default=40.0)
    classify.add_argument("--double-time", type=float, default=0.0)
    classify.add_argument("--daily-threshold", type=float, default=8.0)
    classify.add_argument("--daily-double", type=float, default=12.0)
    classify.add_argument("--state", default="CA")
    classify.set_defaults(func=cmd_classify)

    pto_request = sub.add_parser("request-pto", help="Employee PTO request")
    pto_request.add_argument("employee")
    pto_request.add_argument("date")
    pto_request.add_argument("hours", type=float)
    pto_request.add_argument("--comments")
    pto_request.set_defaults(func=cmd_request_pto)

    pto_approve = sub.add_parser("approve-pto", help="Approve PTO request and convert to time entry")
    pto_approve.add_argument("id")
    pto_approve.add_argument("approver")
    pto_approve.add_argument("pay_period")
    pto_approve.set_defaults(func=cmd_approve_pto)

    timesheet = sub.add_parser("timesheet", help="Render weekly timesheet view")
    timesheet.add_argument("employee")
    timesheet.add_argument("anchor")
    timesheet.set_defaults(func=cmd_timesheet)

    calendar = sub.add_parser("calendar", help="Render calendar view")
    calendar.add_argument("employee")
    calendar.add_argument("year", type=int)
    calendar.add_argument("month", type=int)
    calendar.set_defaults(func=cmd_calendar)

    export = sub.add_parser("export", help="Export entries to CSV")
    export.add_argument("path")
    export.add_argument("--employee")
    export.set_defaults(func=cmd_export)

    imp = sub.add_parser("import", help="Import entries from CSV")
    imp.add_argument("path")
    imp.set_defaults(func=cmd_import)

    pending = sub.add_parser("pending", help="List unapproved entries")
    pending.add_argument("--employee")
    pending.set_defaults(func=cmd_pending)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
