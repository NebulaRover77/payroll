from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .models import CalculationResult, Deduction, EarningLine, EmployeePayrollRequest, ExplanationLine
from .tax_tables import TaxBracket, TaxTable, TaxTableRepository


@dataclass
class PayrollContext:
    tax_table: TaxTable
    period_allowance_divisor: float = 26  # example bi-weekly


class PayrollCalculator:
    def __init__(self, tax_table_repo: TaxTableRepository, table_version: str):
        self.tax_table_repo = tax_table_repo
        self.table_version = table_version
        self.tax_table = tax_table_repo.load(table_version)

    @staticmethod
    def _apply_brackets(amount: float, brackets: List[TaxBracket]) -> float:
        remaining = amount
        last_cap = 0.0
        total_tax = 0.0
        for bracket in brackets:
            taxable_at_rate = max(min(remaining, bracket.up_to - last_cap), 0)
            total_tax += taxable_at_rate * bracket.rate
            remaining -= taxable_at_rate
            last_cap = bracket.up_to
            if remaining <= 0:
                break
        if remaining > 0 and brackets:
            total_tax += remaining * brackets[-1].rate
        return round(total_tax, 2)

    def _apply_deductions(self, wages: float, deductions: List[Deduction], explanations: List[ExplanationLine]) -> Tuple[float, Dict[str, float]]:
        sorted_deductions = sorted(deductions)
        deducted_totals: Dict[str, float] = {}
        taxable_basis = wages
        post_tax_to_apply: List[Tuple[Deduction, float]] = []

        for deduction in sorted_deductions:
            value = deduction.compute_value(taxable_basis if deduction.calculation == "percent" else wages)
            if deduction.applies_pre_tax:
                taxable_basis = max(taxable_basis - value, 0)
            else:
                post_tax_to_apply.append((deduction, value))
            deducted_totals[deduction.name] = value
            explanations.append(
                ExplanationLine(
                    code="deduction",
                    label=deduction.name,
                    amount=value,
                    details={"priority": deduction.priority, "basis": taxable_basis},
                )
            )
        return taxable_basis, dict(deducted_totals), post_tax_to_apply

    def _apply_taxes(self, taxable_wages: float, profile, ctx: PayrollContext, explanations: List[ExplanationLine]) -> Dict[str, float]:
        allowance = ctx.tax_table.allowance_for("federal")
        allowance_reduction = allowance * profile.allowances / ctx.period_allowance_divisor
        adjusted_wages = max(taxable_wages - allowance_reduction, 0)
        federal_tax = self._apply_brackets(
            adjusted_wages,
            ctx.tax_table.brackets_for("federal", profile.filing_status),
        )
        explanations.append(
            ExplanationLine(
                code="federal_tax",
                label="Federal withholding",
                amount=federal_tax,
                details={"adjusted_wages": adjusted_wages},
            )
        )

        state_tax = 0.0
        if profile.state:
            state_allowance = ctx.tax_table.allowance_for("state", profile.state)
            state_adjusted = max(taxable_wages - (state_allowance * profile.allowances / ctx.period_allowance_divisor), 0)
            state_tax = self._apply_brackets(
                state_adjusted,
                ctx.tax_table.brackets_for("state", profile.filing_status, state=profile.state),
            )
            explanations.append(
                ExplanationLine(
                    code="state_tax",
                    label=f"{profile.state} withholding",
                    amount=state_tax,
                    details={"adjusted_wages": state_adjusted},
                )
            )

        return {"federal": federal_tax, "state": state_tax}

    def _employer_taxes(self, taxable_wages: float) -> Dict[str, float]:
        taxes = {}
        for name, cfg in self.tax_table.employer_taxes.items():
            rate = cfg.get("rate", 0)
            wage_base = cfg.get("wage_base")
            basis = min(taxable_wages, wage_base) if wage_base else taxable_wages
            taxes[name] = round(basis * rate, 2)
        return taxes

    def calculate_employee(self, request: EmployeePayrollRequest) -> CalculationResult:
        explanations: List[ExplanationLine] = []
        gross_pay = round(sum(e.amount for e in request.earnings), 2)
        for earning in request.earnings:
            explanations.append(
                ExplanationLine(
                    code=f"earning:{earning.category}",
                    label=f"{earning.category.title()} pay",
                    amount=earning.amount,
                    details={"hours": earning.hours, "rate": earning.rate},
                )
            )

        ctx = PayrollContext(tax_table=self.tax_table)
        taxable_wages, deduction_totals, post_tax_deductions = self._apply_deductions(
            gross_pay, request.deductions, explanations
        )

        tax_withheld = self._apply_taxes(taxable_wages, request.tax_profile, ctx, explanations)
        net_after_taxes = taxable_wages - sum(tax_withheld.values())

        for deduction, value in post_tax_deductions:
            net_after_taxes = max(net_after_taxes - value, 0)
            explanations.append(
                ExplanationLine(
                    code="post_tax_deduction",
                    label=deduction.name,
                    amount=value,
                    details={"priority": deduction.priority},
                )
            )

        employer_taxes = self._employer_taxes(taxable_wages)
        net_pay = round(net_after_taxes, 2)

        return CalculationResult(
            employee_id=request.employee_id,
            gross_pay=gross_pay,
            taxable_wages=taxable_wages,
            taxes_withheld=tax_withheld,
            employee_deductions=deduction_totals,
            employer_taxes=employer_taxes,
            net_pay=net_pay,
            explanations=explanations,
        )
