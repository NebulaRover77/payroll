from pathlib import Path

from payroll.calculator import PayrollCalculator
from payroll.models import Deduction, EarningLine, EmployeePayrollRequest, TaxProfile
from payroll.tax_tables import TaxTableRepository
from payroll.wizard import PreviewWizard


def build_calculator(version: str = "2024_v1") -> PayrollCalculator:
    repo = TaxTableRepository(Path(__file__).resolve().parent.parent / "data" / "tax_tables")
    return PayrollCalculator(repo, version)


def test_pre_tax_deductions_reduce_taxable_wages():
    calc = build_calculator()
    request = EmployeePayrollRequest(
        employee_id="emp1",
        earnings=[EarningLine("regular", hours=80, rate=25)],
        deductions=[
            Deduction(priority=1, name="401k", amount=0.05, calculation="percent", applies_pre_tax=True, limit=300),
            Deduction(priority=2, name="garnishment", amount=50, applies_pre_tax=False),
        ],
        tax_profile=TaxProfile(filing_status="single", allowances=1, state="CA"),
    )

    result = calc.calculate_employee(request)

    assert result.gross_pay == 2000
    assert result.taxable_wages < result.gross_pay  # 401k applied pre-tax
    assert result.employee_deductions["401k"] == 100.0
    assert result.employee_deductions["garnishment"] == 50
    assert result.net_pay < result.gross_pay
    assert any(e.code == "federal_tax" for e in result.explanations)


def test_tax_table_versions_change_output():
    calc_2024 = build_calculator("2024_v1")
    calc_2025 = build_calculator("2025_v1")
    request = EmployeePayrollRequest(
        employee_id="emp2",
        earnings=[EarningLine("regular", hours=40, rate=30)],
        tax_profile=TaxProfile(filing_status="single", allowances=0, state="CA"),
    )

    result_2024 = calc_2024.calculate_employee(request)
    result_2025 = calc_2025.calculate_employee(request)

    assert result_2024.taxes_withheld != result_2025.taxes_withheld
    assert calc_2024.tax_table.version != calc_2025.tax_table.version


def test_preview_wizard_aggregates_totals():
    calc = build_calculator()
    wizard = PreviewWizard(calc)

    requests = [
        EmployeePayrollRequest(
            employee_id="emp1",
            earnings=[EarningLine("regular", hours=40, rate=20)],
            tax_profile=TaxProfile(filing_status="single", allowances=0, state="CA"),
        ),
        EmployeePayrollRequest(
            employee_id="emp2",
            earnings=[EarningLine("regular", hours=45, rate=22)],
            tax_profile=TaxProfile(filing_status="single", allowances=1, state="CA"),
        ),
    ]

    totals = wizard.preview(requests)

    assert set(totals.employees.keys()) == {"emp1", "emp2"}
    assert totals.total_net_pay > 0
    assert totals.gross_pay > 0
    assert totals.employer_taxes
    assert totals.taxes_withheld["federal"] > 0
