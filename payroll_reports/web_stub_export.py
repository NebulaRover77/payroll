from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ReportRow = Dict[str, Any]
DEFAULT_PAY_TYPES = [
    {"id": "regular", "name": "Regular"},
    {"id": "vacation", "name": "Vacation"},
    {"id": "holiday", "name": "Holiday"},
]
SS_RATE = 0.062
MEDICARE_RATE = 0.0145
SS_WAGE_BASE = 160200
STANDARD_DEDUCTION = {"married": 12900, "single": 8600, "head": 8600}


@dataclass(frozen=True)
class StubContext:
    employer_name: str
    employer_address: str
    employer_phone: str
    employer_fein: str
    employee_name: str
    employee_id: str
    employee_address: str
    pay_date: str
    pay_period: str
    pay_rate_label: str
    gross_pay: float
    total_taxes: float
    net_pay: float
    ytd_gross: float
    ytd_taxes: float
    ytd_net: float


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"${value:,.2f}"


def _format_address(address: Dict[str, Any] | None) -> str:
    if not address:
        return "—"
    parts = [
        address.get("line1"),
        address.get("line2"),
        ", ".join(filter(None, [address.get("city"), address.get("state")])),
        address.get("postalCode") or address.get("postal_code"),
    ]
    return " ".join(filter(None, parts)) or "—"


def _format_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return "—"
    return parsed.strftime("%b %d, %Y")


def _year_from_date(value: str | None) -> str:
    if not value:
        return ""
    return value.split("-")[0]


def _get_pay_periods(schedule_name: str, schedules: Iterable[ReportRow]) -> int:
    cadence = ""
    for schedule in schedules:
        if schedule.get("name") == schedule_name:
            cadence = schedule.get("cadence", "")
            break
    cadence = (cadence or schedule_name or "").lower()
    mapping = {
        "weekly": 52,
        "biweekly": 26,
        "semimonthly": 24,
        "monthly": 12,
        "quarterly": 4,
        "semiannually": 2,
        "daily": 260,
    }
    return mapping.get(cadence, 26)


def _resolve_filing_status(employee: ReportRow) -> str:
    w4 = employee.get("w4") or {}
    status = w4.get("filing_status")
    if status == "married":
        return "married"
    if status == "head":
        return "head"
    return "single"


def _lookup_percentage_table(
    adjusted_annual: float, filing_status: str, step2_checked: bool
) -> Tuple[float, float, float, float, float]:
    tables = {
        "standard": {
            "married": [
                (0, 19300, 0, 0, 0),
                (19300, 44100, 0, 0.1, 19300),
                (44100, 120100, 2480, 0.12, 44100),
                (120100, 230700, 11600, 0.22, 120100),
                (230700, 422850, 35932, 0.24, 230700),
                (422850, 531750, 82048, 0.32, 422850),
                (531750, 788000, 116896, 0.35, 531750),
                (788000, float("inf"), 206583.5, 0.37, 788000),
            ],
            "single": [
                (0, 7500, 0, 0, 0),
                (7500, 19900, 0, 0.1, 7500),
                (19900, 57900, 1240, 0.12, 19900),
                (57900, 113200, 5800, 0.22, 57900),
                (113200, 209275, 17966, 0.24, 113200),
                (209275, 263725, 41024, 0.32, 209275),
                (263725, 648100, 58448, 0.35, 263725),
                (648100, float("inf"), 192979.25, 0.37, 648100),
            ],
            "head": [
                (0, 15550, 0, 0, 0),
                (15550, 33250, 0, 0.1, 15550),
                (33250, 83000, 1770, 0.12, 33250),
                (83000, 121250, 7740, 0.22, 83000),
                (121250, 217300, 16155, 0.24, 121250),
                (217300, 271750, 39207, 0.32, 217300),
                (271750, 656150, 56631, 0.35, 271750),
                (656150, float("inf"), 191171, 0.37, 656150),
            ],
        },
        "step2": {
            "married": [
                (0, 16100, 0, 0, 0),
                (16100, 28500, 0, 0.1, 16100),
                (28500, 66500, 1240, 0.12, 28500),
                (66500, 121800, 5800, 0.22, 66500),
                (121800, 217875, 17966, 0.24, 121800),
                (217875, 272325, 41024, 0.32, 217875),
                (272325, 400450, 58448, 0.35, 272325),
                (400450, float("inf"), 103291.75, 0.37, 400450),
            ],
            "single": [
                (0, 8050, 0, 0, 0),
                (8050, 14250, 0, 0.1, 8050),
                (14250, 33250, 620, 0.12, 14250),
                (33250, 60900, 2900, 0.22, 33250),
                (60900, 108938, 8983, 0.24, 60900),
                (108938, 136163, 20512, 0.32, 108938),
                (136163, 328350, 29224, 0.35, 136163),
                (328350, float("inf"), 96489.63, 0.37, 328350),
            ],
            "head": [
                (0, 12075, 0, 0, 0),
                (12075, 20925, 0, 0.1, 12075),
                (20925, 45800, 885, 0.12, 20925),
                (45800, 64925, 3870, 0.22, 45800),
                (64925, 112950, 8077.5, 0.24, 64925),
                (112950, 140175, 19603.5, 0.32, 112950),
                (140175, 332375, 28315.5, 0.35, 140175),
                (332375, float("inf"), 95585.5, 0.37, 332375),
            ],
        },
    }
    key = "step2" if step2_checked else "standard"
    for row in tables[key][filing_status]:
        if adjusted_annual >= row[0] and adjusted_annual < row[1]:
            return row
    return (0, 0, 0, 0, 0)


def _compute_fit(gross: float, employee: ReportRow, schedules: Iterable[ReportRow]) -> float:
    w4 = employee.get("w4") or {}
    if w4.get("tax_exempt"):
        return 0.0
    pay_periods = _get_pay_periods(employee.get("pay_schedule", ""), schedules)
    filing_status = _resolve_filing_status(employee)
    step2_checked = bool(w4.get("box2c_checked"))
    step3_credits = float(w4.get("step3") or 0)
    step4a = float(w4.get("step4a") or 0)
    step4b = float(w4.get("step4b") or 0)
    step4c = float(w4.get("step4c") or 0)
    annualized = gross * pay_periods
    adjusted_annual = max(
        0.0,
        annualized + step4a - (step4b + (0 if step2_checked else STANDARD_DEDUCTION[filing_status])),
    )
    start, _, base, rate, excess_over = _lookup_percentage_table(
        adjusted_annual, filing_status, step2_checked
    )
    tentative_annual = base + max(0.0, adjusted_annual - excess_over) * rate
    tentative_per_period = tentative_annual / pay_periods
    credit_per_period = step3_credits / pay_periods
    after_credits = max(0.0, tentative_per_period - credit_per_period)
    return after_credits + step4c


def _compute_taxes(
    gross: float, employee: ReportRow, ytd_gross: float | None, schedules: Iterable[ReportRow]
) -> Dict[str, float]:
    w4 = employee.get("w4") or {}
    w4_exempt = w4.get("tax_exempt")
    tax_exemptions = employee.get("tax_exemptions") or {}
    fica_exempt = bool(tax_exemptions.get("fica_exempt"))
    ss_only_exempt = bool(tax_exemptions.get("ss_only_exempt"))
    fit = 0.0 if w4_exempt else _compute_fit(gross, employee, schedules)
    ss_taxable = gross
    if ytd_gross is not None:
        ss_taxable = max(0.0, min(gross, SS_WAGE_BASE - ytd_gross))
    ss = 0.0 if fica_exempt or ss_only_exempt else ss_taxable * SS_RATE
    medicare = 0.0 if fica_exempt else gross * MEDICARE_RATE
    total_employee_taxes = fit + ss + medicare
    return {"fit": fit, "ss": ss, "medicare": medicare, "total_employee_taxes": total_employee_taxes}


def _compute_earnings(entry: ReportRow, employee: ReportRow, pay_types: Iterable[ReportRow]) -> Dict[str, Any]:
    hours_by_type = {ptype["id"]: float(entry.get("hours", {}).get(ptype["id"], 0)) for ptype in pay_types}
    total_hours = sum(hours_by_type.values())
    rate = float(employee.get("pay_rate") or 0.0)
    is_salary = employee.get("pay_rate_type") == "period"
    earnings_lines = []
    for pay_type in pay_types:
        hours = hours_by_type.get(pay_type["id"], 0.0)
        amount = hours * rate
        if is_salary:
            amount = rate if pay_type["id"] == "regular" else 0.0
        earnings_lines.append(
            {"id": pay_type["id"], "name": pay_type["name"], "hours": hours, "rate": rate, "amount": amount}
        )
    gross = rate if is_salary and total_hours > 0 else sum(line["amount"] for line in earnings_lines)
    return {"gross": gross, "total_hours": total_hours, "rate": rate}


def _sum_year_to_date(
    entries: Iterable[ReportRow],
    employee: ReportRow,
    pay_types: Iterable[ReportRow],
    schedules: Iterable[ReportRow],
    through_date: str,
) -> Tuple[float, Dict[str, float]]:
    year = _year_from_date(through_date)
    ytd_gross = 0.0
    ytd_taxes = {"fit": 0.0, "ss": 0.0, "medicare": 0.0}
    for entry in entries:
        if entry.get("employee_id") != employee.get("id"):
            continue
        if _year_from_date(entry.get("end_date")) != year:
            continue
        if entry.get("end_date") > through_date:
            continue
        earnings = _compute_earnings(entry, employee, pay_types)
        taxes = _compute_taxes(earnings["gross"], employee, ytd_gross, schedules)
        ytd_gross += earnings["gross"]
        ytd_taxes["fit"] += taxes["fit"]
        ytd_taxes["ss"] += taxes["ss"]
        ytd_taxes["medicare"] += taxes["medicare"]
    return ytd_gross, ytd_taxes


def build_stub_context(
    store: ReportRow, setup: ReportRow, entry: ReportRow, employee: ReportRow
) -> StubContext:
    pay_types = store.get("pay_types") or DEFAULT_PAY_TYPES
    schedules = setup.get("paySchedules") or []
    earnings = _compute_earnings(entry, employee, pay_types)
    ytd_gross, ytd_taxes = _sum_year_to_date(
        store.get("time_entries", []), employee, pay_types, schedules, entry.get("end_date")
    )
    taxes = _compute_taxes(earnings["gross"], employee, ytd_gross - earnings["gross"], schedules)
    net_pay = max(0.0, earnings["gross"] - taxes["total_employee_taxes"])
    ytd_net = max(0.0, ytd_gross - (ytd_taxes["fit"] + ytd_taxes["ss"] + ytd_taxes["medicare"]))
    company = setup.get("company") or {}
    addresses = setup.get("addresses") or []
    employer_address = _format_address(
        next(
            (address for address in addresses if address.get("type") == "legal"),
            addresses[0] if addresses else None,
        )
    )
    pay_rate_label = (
        f"{_money(earnings['rate'])} per pay period"
        if employee.get("pay_rate_type") == "period"
        else f"{_money(earnings['rate'])} per hour"
    )
    return StubContext(
        employer_name=company.get("legalName") or "Company",
        employer_address=employer_address,
        employer_phone=(company.get("contact") or {}).get("phone") or "—",
        employer_fein=company.get("ein") or "—",
        employee_name=employee.get("name") or "Employee",
        employee_id=employee.get("id") or "—",
        employee_address=_format_address(
            {
                "line1": employee.get("address_line1"),
                "line2": employee.get("address_line2"),
                "city": employee.get("city"),
                "state": employee.get("state"),
                "postalCode": employee.get("postal_code"),
            }
        ),
        pay_date=_format_date(entry.get("paid_at") or entry.get("end_date")),
        pay_period=f"{_format_date(entry.get('start_date'))} - {_format_date(entry.get('end_date'))}",
        pay_rate_label=pay_rate_label,
        gross_pay=earnings["gross"],
        total_taxes=taxes["total_employee_taxes"],
        net_pay=net_pay,
        ytd_gross=ytd_gross,
        ytd_taxes=ytd_taxes["fit"] + ytd_taxes["ss"] + ytd_taxes["medicare"],
        ytd_net=ytd_net,
    )


def build_pdf(context: StubContext, output_path: Path) -> None:
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle("stub_header", parent=styles["Heading3"], fontSize=11)
    body_style = ParagraphStyle("stub_body", parent=styles["Normal"], fontSize=9.5)

    story: List[Any] = [Paragraph("PAY STUB", styles["Title"])]
    story.append(
        Table(
            [
                [
                    Paragraph(
                        (
                            f"<b>{context.employer_name}</b><br/>{context.employer_address}<br/>"
                            f"{context.employer_phone}<br/>FEIN: {context.employer_fein}"
                        ),
                        body_style,
                    ),
                    Paragraph(
                        (
                            f"<b>{context.employee_name}</b><br/>Employee ID: {context.employee_id}<br/>"
                            f"{context.employee_address}"
                        ),
                        body_style,
                    ),
                ]
            ],
            colWidths=[3.35 * inch, 3.35 * inch],
        )
    )
    story.append(HRFlowable(width="100%"))
    story.append(Spacer(1, 8))
    story.append(
        Table(
            [["Pay date", context.pay_date, "Pay period", context.pay_period]],
            colWidths=[1.0 * inch, 2.5 * inch, 1.0 * inch, 2.2 * inch],
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("Earnings & Summary", header_style))
    earnings_rows = [
        ["Description", "Current", "YTD"],
        ["Pay rate", context.pay_rate_label, "—"],
        ["Gross pay", _money(context.gross_pay), _money(context.ytd_gross)],
        ["Total taxes", _money(context.total_taxes), _money(context.ytd_taxes)],
        ["Net pay", _money(context.net_pay), _money(context.ytd_net)],
    ]
    earnings_table = Table(earnings_rows, colWidths=[3.3 * inch, 1.5 * inch, 1.5 * inch])
    earnings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, -2), (-1, -2), 0.75, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(earnings_table)

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%"))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Taxes (Current vs Year-to-Date)", header_style))
    tax_rows = [
        ["Tax", "Current", "YTD"],
        ["Total employee taxes", _money(context.total_taxes), _money(context.ytd_taxes)],
    ]
    tax_table = Table(tax_rows, colWidths=[3.3 * inch, 1.5 * inch, 1.5 * inch])
    tax_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tax_table)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    doc.build(story)


def load_json(path: Path) -> ReportRow:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a pay stub PDF from stored payroll data.")
    parser.add_argument("--store-path", required=True)
    parser.add_argument("--setup-path", required=True)
    parser.add_argument("--entry-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    store = load_json(Path(args.store_path))
    setup = load_json(Path(args.setup_path))
    entries = store.get("time_entries", [])
    entry = next((item for item in entries if item.get("id") == args.entry_id), None)
    if not entry or entry.get("status") != "paid":
        raise ValueError("Paid time entry not found.")
    employee = next((item for item in store.get("employees", []) if item.get("id") == entry.get("employee_id")), None)
    if not employee:
        raise ValueError("Employee not found for time entry.")

    context = build_stub_context(store, setup, entry, employee)
    build_pdf(context, Path(args.output))


if __name__ == "__main__":
    main()
