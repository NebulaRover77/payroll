from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ReportRow = Dict[str, Any]

EMPLOYER_NAME = "Acme Services, LLC"
EMPLOYER_ADDRESS_1 = "123 Business Rd"
EMPLOYER_ADDRESS_2 = "Orlando, FL 32801"
EMPLOYER_PHONE = "(407) 555-0199"
EMPLOYER_FEIN = "12-3456789"


@dataclass(frozen=True)
class StubContext:
    employee_id: str
    employee_name: str
    employee_address_1: str
    employee_address_2: str
    department: str
    pay_schedule: str
    pay_date: date | None
    pay_period_start: date | None
    pay_period_end: date | None
    hours: float | None
    gross_pay: float
    taxes: float
    deductions: float
    net_pay: float
    ytd_gross: float
    ytd_taxes: float
    ytd_deductions: float
    ytd_net: float


def _money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"${value:,.2f}"


def _fmt_date(value: date | None) -> str:
    if not value:
        return "—"
    return value.strftime("%b %d, %Y")


def _calculate_period(pay_date: date | None, pay_schedule: str) -> tuple[date | None, date | None]:
    if not pay_date:
        return None, None
    schedule = (pay_schedule or "").lower()
    if "monthly" in schedule:
        start = pay_date.replace(day=1)
    elif "biweekly" in schedule:
        start = pay_date - timedelta(days=13)
    else:
        start = pay_date
    return start, pay_date


def _build_stub_contexts(
    payments: Iterable[ReportRow], employees: Iterable[ReportRow]
) -> List[StubContext]:
    employee_index = {employee["employee_id"]: employee for employee in employees}
    payments_by_employee: Dict[str, List[ReportRow]] = {}
    for payment in payments:
        payments_by_employee.setdefault(payment["employee_id"], []).append(payment)

    contexts: List[StubContext] = []
    for employee_id, records in payments_by_employee.items():
        records.sort(key=lambda payment: payment.get("pay_date") or date.min)
        cumulative_gross = 0.0
        cumulative_taxes = 0.0
        cumulative_deductions = 0.0
        for payment in records:
            cumulative_gross += float(payment.get("gross_pay") or 0.0)
            cumulative_taxes += float(payment.get("taxes") or 0.0)
            cumulative_deductions += float(payment.get("deductions") or 0.0)
            net_pay = float(payment.get("net_pay") or 0.0)
            cumulative_net = cumulative_gross - cumulative_taxes - cumulative_deductions
            employee = employee_index.get(employee_id, {})
            pay_schedule = employee.get("pay_schedule") or payment.get("pay_schedule") or "—"
            pay_date = payment.get("pay_date")
            period_start, period_end = _calculate_period(pay_date, pay_schedule)

            contexts.append(
                StubContext(
                    employee_id=employee_id,
                    employee_name=employee.get("name", "Unknown"),
                    employee_address_1=employee.get("address_1", "456 Main St"),
                    employee_address_2=employee.get("address_2", "Orlando, FL 32803"),
                    department=employee.get("department", payment.get("department", "—")),
                    pay_schedule=pay_schedule,
                    pay_date=pay_date,
                    pay_period_start=period_start,
                    pay_period_end=period_end,
                    hours=payment.get("hours"),
                    gross_pay=float(payment.get("gross_pay") or 0.0),
                    taxes=float(payment.get("taxes") or 0.0),
                    deductions=float(payment.get("deductions") or 0.0),
                    net_pay=net_pay,
                    ytd_gross=cumulative_gross,
                    ytd_taxes=cumulative_taxes,
                    ytd_deductions=cumulative_deductions,
                    ytd_net=cumulative_net,
                )
            )

    contexts.sort(key=lambda context: (context.employee_id, context.pay_date or date.min))
    return contexts


def _build_stub_story(context: StubContext) -> List[Any]:
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
                            f"<b>{EMPLOYER_NAME}</b><br/>{EMPLOYER_ADDRESS_1}<br/>"
                            f"{EMPLOYER_ADDRESS_2}<br/>{EMPLOYER_PHONE}<br/>"
                            f"FEIN: {EMPLOYER_FEIN}"
                        ),
                        body_style,
                    ),
                    Paragraph(
                        (
                            f"<b>{context.employee_name}</b><br/>"
                            f"Employee ID: {context.employee_id}<br/>"
                            f"{context.employee_address_1}<br/>{context.employee_address_2}"
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
            [
                [
                    "Pay date",
                    _fmt_date(context.pay_date),
                    "Pay period",
                    f"{_fmt_date(context.pay_period_start)} - {_fmt_date(context.pay_period_end)}",
                ]
            ],
            colWidths=[1.0 * inch, 2.5 * inch, 1.0 * inch, 2.2 * inch],
        )
    )

    story.append(Spacer(1, 10))
    story.append(Paragraph("Earnings & Summary", header_style))

    earnings_rows = [
        ["Description", "Current", "YTD"],
        ["Regular pay", _money(context.gross_pay), _money(context.ytd_gross)],
        ["Gross pay", _money(context.gross_pay), _money(context.ytd_gross)],
        ["Total deductions", _money(context.taxes + context.deductions), _money(context.ytd_taxes + context.ytd_deductions)],
        ["Net pay", _money(context.net_pay), _money(context.ytd_net)],
    ]

    earnings_table = Table(
        earnings_rows,
        colWidths=[3.3 * inch, 1.5 * inch, 1.5 * inch],
    )
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

    story.append(Paragraph("Itemized Deductions (Current vs Year-to-Date)", header_style))

    deduction_rows = [
        ["Deduction", "Current", "YTD"],
        ["Taxes", _money(context.taxes), _money(context.ytd_taxes)],
        ["Other deductions", _money(context.deductions), _money(context.ytd_deductions)],
        [
            Paragraph("<b>Total deductions</b>", body_style),
            Paragraph(f"<b>{_money(context.taxes + context.deductions)}</b>", body_style),
            Paragraph(
                f"<b>{_money(context.ytd_taxes + context.ytd_deductions)}</b>", body_style
            ),
        ],
    ]

    deductions_table = Table(
        deduction_rows,
        colWidths=[3.3 * inch, 1.5 * inch, 1.5 * inch],
    )
    deductions_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -2), 0.25, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
            ]
        )
    )
    story.append(deductions_table)

    return story


def export_check_stub_pdf(
    payments: Iterable[ReportRow], employees: Iterable[ReportRow], output_path: Path
) -> Path:
    contexts = _build_stub_contexts(payments, employees)
    if not contexts:
        contexts = [
            StubContext(
                employee_id="—",
                employee_name="No checks",
                employee_address_1="—",
                employee_address_2="—",
                department="—",
                pay_schedule="—",
                pay_date=None,
                pay_period_start=None,
                pay_period_end=None,
                hours=None,
                gross_pay=0.0,
                taxes=0.0,
                deductions=0.0,
                net_pay=0.0,
                ytd_gross=0.0,
                ytd_taxes=0.0,
                ytd_deductions=0.0,
                ytd_net=0.0,
            )
        ]

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    story: List[Any] = []
    for index, context in enumerate(contexts):
        if index:
            story.append(PageBreak())
        story.extend(_build_stub_story(context))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    return output_path
