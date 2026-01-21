from payroll.models import CalculationResult, Deduction, EarningLine


def test_earning_line_amount_rounds_currency():
    line = EarningLine("regular", hours=1.5, rate=33.333)

    assert line.amount == 50.0


def test_deduction_compute_value_applies_percent_and_limit():
    deduction = Deduction(priority=1, name="401k", amount=0.1, calculation="percent", limit=75)

    assert deduction.compute_value(1000) == 75.0


def test_total_withheld_rounds_sum():
    result = CalculationResult(
        employee_id="emp1",
        gross_pay=1000.0,
        taxable_wages=900.0,
        taxes_withheld={"federal": 100.123},
        employee_deductions={"401k": 50.555},
        employer_taxes={},
        net_pay=0.0,
        explanations=[],
    )

    assert result.total_withheld() == 150.68
