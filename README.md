# Payroll Calculation Engine

This repository provides a deterministic payroll calculation pipeline with versioned tax tables, auditable line-by-line explanations, and preview tooling for running payroll across multiple employees.

## Features
- Earnings ingestion (regular, overtime, PTO) with per-line explanations.
- Pre- and post-tax deductions with ordering and limits (401k, benefits, garnishments).
- Parameterized tax inputs per employee (filing status, allowances, state) applied against federal and state tax tables.
- Versioned tax configuration files stored under `data/tax_tables` with employer tax rules.
- Preview wizard to aggregate totals for employees, with employer tax totals.

## Quickstart
1. Ensure Python 3.11+ is available.
2. Run tests to verify the calculation pipeline:
   ```bash
   pip install -r requirements.txt  # No dependencies required for core logic
   pytest
   ```
3. Example usage:
   ```python
   from pathlib import Path
   from payroll.calculator import PayrollCalculator
   from payroll.models import Deduction, EarningLine, EmployeePayrollRequest, TaxProfile
   from payroll.tax_tables import TaxTableRepository

   repo = TaxTableRepository(Path("data/tax_tables"))
   calculator = PayrollCalculator(repo, "2024_v1")

   request = EmployeePayrollRequest(
       employee_id="emp123",
       earnings=[EarningLine("regular", hours=80, rate=30)],
       deductions=[Deduction(priority=1, name="401k", amount=0.05, calculation="percent", applies_pre_tax=True)],
       tax_profile=TaxProfile(filing_status="single", allowances=1, state="CA"),
   )

   result = calculator.calculate_employee(request)
   print(result.net_pay, result.taxes_withheld, len(result.explanations))
   ```
