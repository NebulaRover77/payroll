from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from . import data
from .audit import AuditLogger
from .check_stub import export_check_stub_pdf
from .exporter import export_report
from .reports import ReportRequest, build_report
from .scheduler import Schedule, Scheduler


REPORT_CHOICES = [
    "payroll-register",
    "payment-detail",
    "deductions-taxes-summary",
    "labor-distribution",
    "check-stub",
]


def parse_date(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value).date()


def run_report(args: argparse.Namespace) -> None:
    if args.report == "check-stub":
        if not args.output:
            raise ValueError("Check stubs must be exported to a PDF file.")
        output_path = Path(args.output)
        if output_path.suffix.lower() != ".pdf":
            raise ValueError("Check stubs are only supported as PDF exports.")
        export_check_stub_pdf(data.payments, data.employees, output_path)
        print(f"Check stubs exported to {output_path}")
    else:
        request = ReportRequest(
            report_type=args.report,
            start_date=parse_date(args.start_date),
            end_date=parse_date(args.end_date),
            pay_schedules=args.pay_schedule,
            departments=args.department,
        )
        rows = build_report(request, data.payments)
        if args.output:
            output_path = Path(args.output)
            export_report(rows, output_path, title=args.report)
            print(f"Report exported to {output_path}")
        else:
            print(json.dumps(rows, default=str, indent=2))

    AuditLogger().log(
        {
            "action": "manual-run",
            "report_type": args.report,
            "filters": {
                "start_date": args.start_date,
                "end_date": args.end_date,
                "pay_schedules": args.pay_schedule,
                "departments": args.department,
            },
            "output": args.output or "stdout",
        }
    )


def add_schedule(args: argparse.Namespace) -> None:
    schedule = Schedule(
        schedule_id=args.id,
        report_type=args.report,
        frequency=args.frequency,
        output_path=args.output,
        start_date=args.start_date,
        end_date=args.end_date,
        pay_schedules=args.pay_schedule,
        departments=args.department,
    )
    Scheduler().add_schedule(schedule)
    print(f"Added schedule {schedule.schedule_id} for {schedule.report_type}")


def run_schedules(_: argparse.Namespace) -> None:
    outputs = Scheduler().run_due_schedules(data.payments)
    if outputs:
        for path in outputs:
            print(f"Generated scheduled report: {path}")
    else:
        print("No schedules due today")


def list_schedules(_: argparse.Namespace) -> None:
    schedules = Scheduler().list_schedules()
    print(json.dumps([schedule.__dict__ for schedule in schedules], indent=2))


def remove_schedule(args: argparse.Namespace) -> None:
    Scheduler().remove_schedule(args.id)
    print(f"Removed schedule {args.id}")


def show_audit(_: argparse.Namespace) -> None:
    records = AuditLogger().read()
    print(json.dumps(records, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Payroll reporting utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_cmd = subparsers.add_parser("run-report", help="Run a single report")
    run_cmd.add_argument("--report", choices=REPORT_CHOICES, required=True)
    run_cmd.add_argument("--start-date")
    run_cmd.add_argument("--end-date")
    run_cmd.add_argument("--pay-schedule", action="append")
    run_cmd.add_argument("--department", action="append")
    run_cmd.add_argument("--output", help="Output file (csv or pdf)")
    run_cmd.set_defaults(func=run_report)

    schedule_cmd = subparsers.add_parser("schedule-add", help="Add a scheduled report")
    schedule_cmd.add_argument("--id", required=True, help="Unique schedule id")
    schedule_cmd.add_argument("--report", choices=REPORT_CHOICES, required=True)
    schedule_cmd.add_argument("--frequency", choices=["daily", "weekly"], required=True)
    schedule_cmd.add_argument("--start-date")
    schedule_cmd.add_argument("--end-date")
    schedule_cmd.add_argument("--pay-schedule", action="append")
    schedule_cmd.add_argument("--department", action="append")
    schedule_cmd.add_argument("--output", required=True, help="Output file (csv or pdf)")
    schedule_cmd.set_defaults(func=add_schedule)

    schedule_run_cmd = subparsers.add_parser("schedule-run", help="Run any due schedules")
    schedule_run_cmd.set_defaults(func=run_schedules)

    schedule_list_cmd = subparsers.add_parser("schedule-list", help="List schedules")
    schedule_list_cmd.set_defaults(func=list_schedules)

    schedule_remove_cmd = subparsers.add_parser("schedule-remove", help="Remove a schedule")
    schedule_remove_cmd.add_argument("--id", required=True)
    schedule_remove_cmd.set_defaults(func=remove_schedule)

    audit_cmd = subparsers.add_parser("audit", help="Show audit log")
    audit_cmd.set_defaults(func=show_audit)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
