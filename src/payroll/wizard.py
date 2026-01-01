from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .calculator import PayrollCalculator
from .models import CalculationResult, EmployeePayrollRequest


@dataclass
class PreviewTotals:
    employees: Dict[str, CalculationResult]
    employer_taxes: Dict[str, float]
    total_net_pay: float
    gross_pay: float
    taxes_withheld: Dict[str, float]


class PreviewWizard:
    def __init__(self, calculator: PayrollCalculator):
        self.calculator = calculator

    def preview(self, requests: List[EmployeePayrollRequest]) -> PreviewTotals:
        employee_results: Dict[str, CalculationResult] = {}
        employer_taxes: Dict[str, float] = {}
        total_net = 0.0
        total_gross = 0.0
        withheld_totals: Dict[str, float] = {}

        for request in requests:
            result = self.calculator.calculate_employee(request)
            employee_results[request.employee_id] = result
            total_net += result.net_pay
            total_gross += result.gross_pay
            for tax_name, value in result.employer_taxes.items():
                employer_taxes[tax_name] = employer_taxes.get(tax_name, 0) + value
            for tax_name, value in result.taxes_withheld.items():
                withheld_totals[tax_name] = withheld_totals.get(tax_name, 0) + value

        return PreviewTotals(
            employees=employee_results,
            employer_taxes={k: round(v, 2) for k, v in employer_taxes.items()},
            total_net_pay=round(total_net, 2),
            gross_pay=round(total_gross, 2),
            taxes_withheld={k: round(v, 2) for k, v in withheld_totals.items()},
        )
