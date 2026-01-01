from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class EarningLine:
    category: str  # e.g. regular, overtime, pto
    hours: float
    rate: float

    @property
    def amount(self) -> float:
        return round(self.hours * self.rate, 2)


@dataclass(order=True)
class Deduction:
    priority: int
    name: str
    amount: float
    calculation: str = "flat"  # flat or percent
    applies_pre_tax: bool = True
    limit: Optional[float] = None

    def compute_value(self, basis: float) -> float:
        if self.calculation == "percent":
            raw = basis * self.amount
        else:
            raw = self.amount
        value = min(raw, self.limit) if self.limit is not None else raw
        return round(value, 2)


@dataclass
class TaxProfile:
    filing_status: str
    allowances: int = 0
    state: str = ""  # e.g. CA, NY


@dataclass
class EmployeePayrollRequest:
    employee_id: str
    earnings: List[EarningLine]
    deductions: List[Deduction] = field(default_factory=list)
    tax_profile: TaxProfile = field(default_factory=TaxProfile)
    custom_tax_inputs: Dict[str, float] = field(default_factory=dict)


@dataclass
class ExplanationLine:
    code: str
    label: str
    amount: float
    details: Dict[str, float] = field(default_factory=dict)


@dataclass
class CalculationResult:
    employee_id: str
    gross_pay: float
    taxable_wages: float
    taxes_withheld: Dict[str, float]
    employee_deductions: Dict[str, float]
    employer_taxes: Dict[str, float]
    net_pay: float
    explanations: List[ExplanationLine]

    def total_withheld(self) -> float:
        return round(sum(self.taxes_withheld.values()) + sum(self.employee_deductions.values()), 2)
