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
    employee_ids: List[str] | None = None
    group_by: str | None = None
    year: int | None = None
    quarter: int | None = None


ReportRow = Dict[str, Any]


def _round_dict(values: Dict[str, float]) -> Dict[str, float]:
    return {key: round(value, 2) for key, value in values.items()}


def _aggregate_by_type(payments: Iterable[ReportRow], field: str, amount_key: str) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for payment in payments:
        for item in payment.get(field, []):
            totals[item["type"]] += float(item.get(amount_key, 0.0))
    return _round_dict(totals)


def _aggregate_hours_by_type(payments: Iterable[ReportRow], field: str) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for payment in payments:
        for item in payment.get(field, []):
            totals[item["type"]] += float(item.get("hours", 0.0))
    return _round_dict(totals)


def _aggregate_tax_map(payments: Iterable[ReportRow], field: str) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for payment in payments:
        for key, value in payment.get(field, {}).items():
            totals[key] += float(value)
    return _round_dict(totals)


def _aggregate_payments(payments: Iterable[ReportRow]) -> Dict[str, Any]:
    payment_list = list(payments)
    earnings_by_type = _aggregate_by_type(payment_list, "earnings", "amount")
    hours_by_type = _aggregate_hours_by_type(payment_list, "earnings")
    deductions_by_type = _aggregate_by_type(payment_list, "deductions_detail", "amount")
    contributions_by_type = _aggregate_by_type(payment_list, "contributions_detail", "amount")
    employee_taxes = _aggregate_tax_map(payment_list, "employee_taxes")
    employer_taxes = _aggregate_tax_map(payment_list, "employer_taxes")
    taxable_wages = _aggregate_tax_map(payment_list, "taxable_wages")

    return {
        "earnings_by_type": earnings_by_type,
        "earnings_total": round(sum(earnings_by_type.values()), 2),
        "hours_by_type": hours_by_type,
        "hours_total": round(sum(hours_by_type.values()), 2),
        "deductions_by_type": deductions_by_type,
        "deductions_total": round(sum(deductions_by_type.values()), 2),
        "contributions_by_type": contributions_by_type,
        "contributions_total": round(sum(contributions_by_type.values()), 2),
        "employee_taxes": employee_taxes,
        "employee_taxes_total": round(sum(employee_taxes.values()), 2),
        "employer_taxes": employer_taxes,
        "employer_taxes_total": round(sum(employer_taxes.values()), 2),
        "taxable_wages": taxable_wages,
    }


def _quarter_for_date(pay_date: date) -> int:
    return (pay_date.month - 1) // 3 + 1


def _resolve_year(request: ReportRequest, payments: Iterable[ReportRow]) -> int:
    if request.year:
        return request.year
    if request.start_date:
        return request.start_date.year
    payment_list = list(payments)
    if not payment_list:
        raise ValueError("No payments available to resolve reporting year.")
    return payment_list[0]["pay_date"].year


def payroll_details(payments: Iterable[ReportRow], group_by: str | None = None) -> List[ReportRow]:
    payment_list = list(payments)
    rows: List[ReportRow] = []
    group_by = (group_by or "none").lower()

    if group_by == "pay_date":
        grouped: Dict[date, List[ReportRow]] = defaultdict(list)
        for payment in payment_list:
            grouped[payment["pay_date"]].append(payment)
        for pay_date, bucket in sorted(grouped.items(), key=lambda item: item[0]):
            totals = _aggregate_payments(bucket)
            rows.append(
                {
                    "group_by": "pay_date",
                    "pay_date": pay_date,
                    "employee_id": "ALL",
                    "employee_name": "All employees",
                    **totals,
                }
            )
        return rows

    if group_by == "employee":
        grouped: Dict[str, List[ReportRow]] = defaultdict(list)
        for payment in payment_list:
            grouped[payment["employee_id"]].append(payment)
        for employee_id, bucket in grouped.items():
            totals = _aggregate_payments(bucket)
            rows.append(
                {
                    "group_by": "employee",
                    "employee_id": employee_id,
                    "employee_name": bucket[0].get("employee_name", employee_id),
                    "pay_date": None,
                    **totals,
                }
            )
        return rows

    for payment in payment_list:
        totals = _aggregate_payments([payment])
        rows.append(
            {
                "group_by": "none",
                "pay_date": payment["pay_date"],
                "employee_id": payment["employee_id"],
                "employee_name": payment.get("employee_name", payment["employee_id"]),
                **totals,
            }
        )
    return rows


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


def form_940_summary(payments: Iterable[ReportRow], request: ReportRequest) -> List[ReportRow]:
    payment_list = list(payments)
    year = _resolve_year(request, payment_list)
    rows: List[ReportRow] = []
    year_payments = [p for p in payment_list if p["pay_date"].year == year]
    taxable_wages = _aggregate_tax_map(year_payments, "taxable_wages")
    employer_taxes = _aggregate_tax_map(year_payments, "employer_taxes")
    rows.append(
        {
            "year": year,
            "futa_taxable_wages": taxable_wages.get("futa", 0.0),
            "futa_tax": employer_taxes.get("futa", 0.0),
            "total_gross_wages": round(sum(p["gross_pay"] for p in year_payments), 2),
        }
    )
    return rows


def form_941_summary(payments: Iterable[ReportRow], request: ReportRequest) -> List[ReportRow]:
    payment_list = list(payments)
    year = _resolve_year(request, payment_list)
    quarter = request.quarter
    if quarter is None and request.start_date:
        quarter = _quarter_for_date(request.start_date)
    if quarter is None:
        quarter = 1
    quarter_payments = [
        p for p in payment_list if p["pay_date"].year == year and _quarter_for_date(p["pay_date"]) == quarter
    ]
    taxable_wages = _aggregate_tax_map(quarter_payments, "taxable_wages")
    employee_taxes = _aggregate_tax_map(quarter_payments, "employee_taxes")
    employer_taxes = _aggregate_tax_map(quarter_payments, "employer_taxes")
    return [
        {
            "year": year,
            "quarter": quarter,
            "fit_taxable_wages": taxable_wages.get("fit", 0.0),
            "ss_taxable_wages": taxable_wages.get("ss", 0.0),
            "medicare_taxable_wages": taxable_wages.get("medicare", 0.0),
            "employee_fit_tax": employee_taxes.get("fit", 0.0),
            "employee_ss_tax": employee_taxes.get("ss", 0.0),
            "employee_medicare_tax": employee_taxes.get("medicare", 0.0),
            "employer_fit_tax": employer_taxes.get("fit", 0.0),
            "employer_ss_tax": employer_taxes.get("ss", 0.0),
            "employer_medicare_tax": employer_taxes.get("medicare", 0.0),
        }
    ]


def payroll_tax_liabilities(payments: Iterable[ReportRow]) -> List[ReportRow]:
    payment_list = list(payments)
    rows: List[ReportRow] = []
    taxable_wages = _aggregate_tax_map(payment_list, "taxable_wages")
    employee_taxes = _aggregate_tax_map(payment_list, "employee_taxes")
    employer_taxes = _aggregate_tax_map(payment_list, "employer_taxes")

    for tax_key, label in [("fit", "FIT"), ("ss", "SS"), ("medicare", "Medicare")]:
        ee_tax = employee_taxes.get(tax_key, 0.0)
        er_tax = employer_taxes.get(tax_key, 0.0)
        rows.append(
            {
                "section": "federal",
                "tax_type": label,
                "taxable_wages": taxable_wages.get(tax_key, 0.0),
                "employee_taxes": ee_tax,
                "employer_taxes": er_tax,
                "total_taxes": round(ee_tax + er_tax, 2),
            }
        )

    suta_rows: Dict[str, Dict[str, float]] = defaultdict(lambda: {"gross": 0.0, "taxable": 0.0, "tax": 0.0})
    futa_rows: Dict[str, Dict[str, float]] = defaultdict(lambda: {"gross": 0.0, "taxable": 0.0, "tax": 0.0})
    for payment in payment_list:
        employee_id = payment["employee_id"]
        suta_rows[employee_id]["gross"] += float(payment["gross_pay"])
        suta_rows[employee_id]["taxable"] += float(payment.get("taxable_wages", {}).get("suta", 0.0))
        suta_rows[employee_id]["tax"] += float(payment.get("employer_taxes", {}).get("suta", 0.0))
        futa_rows[employee_id]["gross"] += float(payment["gross_pay"])
        futa_rows[employee_id]["taxable"] += float(payment.get("taxable_wages", {}).get("futa", 0.0))
        futa_rows[employee_id]["tax"] += float(payment.get("employer_taxes", {}).get("futa", 0.0))

    for employee_id, values in suta_rows.items():
        rows.append(
            {
                "section": "suta",
                "employee_id": employee_id,
                "employee_name": next(
                    (p.get("employee_name") for p in payment_list if p["employee_id"] == employee_id), employee_id
                ),
                "gross_wages": round(values["gross"], 2),
                "taxable_wages": round(values["taxable"], 2),
                "taxes": round(values["tax"], 2),
            }
        )

    for employee_id, values in futa_rows.items():
        rows.append(
            {
                "section": "futa",
                "employee_id": employee_id,
                "employee_name": next(
                    (p.get("employee_name") for p in payment_list if p["employee_id"] == employee_id), employee_id
                ),
                "gross_wages": round(values["gross"], 2),
                "taxable_wages": round(values["taxable"], 2),
                "taxes": round(values["tax"], 2),
            }
        )

    return rows


def tax_deposits(payments: Iterable[ReportRow]) -> List[ReportRow]:
    payment_list = list(payments)
    rows: List[ReportRow] = []
    grouped: Dict[date, List[ReportRow]] = defaultdict(list)
    for payment in payment_list:
        grouped[payment["pay_date"]].append(payment)

    for pay_date, bucket in sorted(grouped.items(), key=lambda item: item[0]):
        employee_taxes = _aggregate_tax_map(bucket, "employee_taxes")
        employer_taxes = _aggregate_tax_map(bucket, "employer_taxes")
        fit_total = employee_taxes.get("fit", 0.0) + employer_taxes.get("fit", 0.0)
        ss_total = employee_taxes.get("ss", 0.0) + employer_taxes.get("ss", 0.0)
        medicare_total = employee_taxes.get("medicare", 0.0) + employer_taxes.get("medicare", 0.0)
        suta_total = employer_taxes.get("suta", 0.0)
        futa_total = employer_taxes.get("futa", 0.0)
        total = round(fit_total + ss_total + medicare_total + suta_total + futa_total, 2)
        rows.append(
            {
                "pay_date": pay_date,
                "fit_total": round(fit_total, 2),
                "ss_total": round(ss_total, 2),
                "medicare_total": round(medicare_total, 2),
                "suta_total": round(suta_total, 2),
                "futa_total": round(futa_total, 2),
                "total_tax_deposit": total,
            }
        )
    return rows


def w2_w3_summary(payments: Iterable[ReportRow], request: ReportRequest) -> List[ReportRow]:
    payment_list = list(payments)
    year = _resolve_year(request, payment_list)
    year_payments = [p for p in payment_list if p["pay_date"].year == year]
    grouped: Dict[str, List[ReportRow]] = defaultdict(list)
    for payment in year_payments:
        grouped[payment["employee_id"]].append(payment)

    rows: List[ReportRow] = []
    totals = defaultdict(float)

    for employee_id, bucket in grouped.items():
        taxable_wages = _aggregate_tax_map(bucket, "taxable_wages")
        employee_taxes = _aggregate_tax_map(bucket, "employee_taxes")
        gross_wages = round(sum(p["gross_pay"] for p in bucket), 2)
        row = {
            "year": year,
            "employee_id": employee_id,
            "employee_name": bucket[0].get("employee_name", employee_id),
            "gross_wages": gross_wages,
            "fit_wages": taxable_wages.get("fit", 0.0),
            "ss_wages": taxable_wages.get("ss", 0.0),
            "medicare_wages": taxable_wages.get("medicare", 0.0),
            "fit_withheld": employee_taxes.get("fit", 0.0),
            "ss_withheld": employee_taxes.get("ss", 0.0),
            "medicare_withheld": employee_taxes.get("medicare", 0.0),
        }
        rows.append(row)
        totals["gross_wages"] += gross_wages
        totals["fit_wages"] += taxable_wages.get("fit", 0.0)
        totals["ss_wages"] += taxable_wages.get("ss", 0.0)
        totals["medicare_wages"] += taxable_wages.get("medicare", 0.0)
        totals["fit_withheld"] += employee_taxes.get("fit", 0.0)
        totals["ss_withheld"] += employee_taxes.get("ss", 0.0)
        totals["medicare_withheld"] += employee_taxes.get("medicare", 0.0)

    rows.append(
        {
            "year": year,
            "employee_id": "TOTAL",
            "employee_name": "W-3 Totals",
            "gross_wages": round(totals["gross_wages"], 2),
            "fit_wages": round(totals["fit_wages"], 2),
            "ss_wages": round(totals["ss_wages"], 2),
            "medicare_wages": round(totals["medicare_wages"], 2),
            "fit_withheld": round(totals["fit_withheld"], 2),
            "ss_withheld": round(totals["ss_withheld"], 2),
            "medicare_withheld": round(totals["medicare_withheld"], 2),
        }
    )
    return rows


def electronic_w2_placeholder(_: Iterable[ReportRow], request: ReportRequest) -> List[ReportRow]:
    year = request.year
    return [
        {
            "year": year,
            "status": "not_implemented",
            "message": "Electronic W-2 SSA upload is planned but not yet implemented.",
        }
    ]


REPORT_BUILDERS = {
    "payroll-register": payroll_register,
    "payment-detail": payment_detail,
    "deductions-taxes-summary": deductions_and_taxes_summary,
    "labor-distribution": labor_distribution,
    "payroll-tax-liabilities": payroll_tax_liabilities,
    "tax-deposits": tax_deposits,
}


def build_report(request: ReportRequest, payments: Iterable[ReportRow]) -> List[ReportRow]:
    filtered = filter_payments(
        payments,
        start_date=request.start_date,
        end_date=request.end_date,
        pay_schedules=request.pay_schedules,
        departments=request.departments,
        employee_ids=request.employee_ids,
    )
    if request.report_type == "payroll-details":
        return payroll_details(filtered, group_by=request.group_by)
    if request.report_type == "form-940":
        return form_940_summary(filtered, request)
    if request.report_type == "form-941":
        return form_941_summary(filtered, request)
    if request.report_type == "w2-w3":
        return w2_w3_summary(filtered, request)
    if request.report_type == "electronic-w2":
        return electronic_w2_placeholder(filtered, request)
    try:
        builder = REPORT_BUILDERS[request.report_type]
    except KeyError as exc:
        raise ValueError(f"Unknown report type: {request.report_type}") from exc
    return builder(filtered)
