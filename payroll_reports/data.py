from __future__ import annotations

from datetime import date
from typing import List, Dict, Any

# Sample employee and payment data used for demonstrations and tests.
# In a real application this would come from a database or payroll system.

EmployeeRecord = Dict[str, Any]
PaymentRecord = Dict[str, Any]

employees: List[EmployeeRecord] = [
    {
        "employee_id": "E001",
        "name": "Avery Rivera",
        "department": "Engineering",
        "project": "Timekeeping",
        "pay_schedule": "Biweekly",
    },
    {
        "employee_id": "E002",
        "name": "Samir Patel",
        "department": "Engineering",
        "project": "Integrations",
        "pay_schedule": "Monthly",
    },
    {
        "employee_id": "E003",
        "name": "Morgan Lee",
        "department": "Support",
        "project": "Customer Success",
        "pay_schedule": "Biweekly",
    },
]

payments: List[PaymentRecord] = [
    {
        "employee_id": "E001",
        "employee_name": "Avery Rivera",
        "pay_date": date(2024, 7, 12),
        "gross_pay": 4200.00,
        "net_pay": 3200.00,
        "taxes": 750.00,
        "deductions": 250.00,
        "hours": 80,
        "department": "Engineering",
        "project": "Timekeeping",
        "pay_schedule": "Biweekly",
        "earnings": [
            {"type": "Regular", "hours": 70, "amount": 3500.00},
            {"type": "Overtime", "hours": 10, "amount": 700.00},
        ],
        "deductions_detail": [
            {"type": "Medical", "amount": 150.00},
            {"type": "401k", "amount": 100.00},
        ],
        "contributions_detail": [
            {"type": "401k Match", "amount": 120.00},
        ],
        "employee_taxes": {"fit": 400.00, "ss": 260.00, "medicare": 90.00},
        "employer_taxes": {"fit": 60.00, "ss": 260.00, "medicare": 90.00, "futa": 42.00, "suta": 84.00},
        "taxable_wages": {
            "fit": 4200.00,
            "ss": 4200.00,
            "medicare": 4200.00,
            "futa": 4200.00,
            "suta": 4200.00,
        },
        "allocations": [
            {"department": "Engineering", "project": "Timekeeping", "hours": 60, "wages": 3150.00},
            {"department": "Engineering", "project": "Platform", "hours": 20, "wages": 1050.00},
        ],
    },
    {
        "employee_id": "E001",
        "employee_name": "Avery Rivera",
        "pay_date": date(2024, 7, 26),
        "gross_pay": 4250.00,
        "net_pay": 3250.00,
        "taxes": 760.00,
        "deductions": 240.00,
        "hours": 80,
        "department": "Engineering",
        "project": "Timekeeping",
        "pay_schedule": "Biweekly",
        "earnings": [
            {"type": "Regular", "hours": 70, "amount": 3600.00},
            {"type": "Overtime", "hours": 10, "amount": 650.00},
        ],
        "deductions_detail": [
            {"type": "Medical", "amount": 140.00},
            {"type": "401k", "amount": 100.00},
        ],
        "contributions_detail": [
            {"type": "401k Match", "amount": 120.00},
        ],
        "employee_taxes": {"fit": 410.00, "ss": 265.00, "medicare": 85.00},
        "employer_taxes": {"fit": 60.00, "ss": 265.00, "medicare": 85.00, "futa": 42.50, "suta": 85.00},
        "taxable_wages": {
            "fit": 4250.00,
            "ss": 4250.00,
            "medicare": 4250.00,
            "futa": 4250.00,
            "suta": 4250.00,
        },
        "allocations": [
            {"department": "Engineering", "project": "Timekeeping", "hours": 50, "wages": 2650.00},
            {"department": "Engineering", "project": "Integrations", "hours": 30, "wages": 1600.00},
        ],
    },
    {
        "employee_id": "E002",
        "employee_name": "Samir Patel",
        "pay_date": date(2024, 7, 31),
        "gross_pay": 6000.00,
        "net_pay": 4400.00,
        "taxes": 1200.00,
        "deductions": 400.00,
        "hours": 160,
        "department": "Engineering",
        "project": "Integrations",
        "pay_schedule": "Monthly",
        "earnings": [
            {"type": "Salary", "hours": 160, "amount": 5800.00},
            {"type": "Bonus", "hours": 0, "amount": 200.00},
        ],
        "deductions_detail": [
            {"type": "Medical", "amount": 250.00},
            {"type": "HSA", "amount": 150.00},
        ],
        "contributions_detail": [
            {"type": "HSA Match", "amount": 100.00},
        ],
        "employee_taxes": {"fit": 700.00, "ss": 372.00, "medicare": 128.00},
        "employer_taxes": {"fit": 90.00, "ss": 372.00, "medicare": 128.00, "futa": 60.00, "suta": 120.00},
        "taxable_wages": {
            "fit": 6000.00,
            "ss": 6000.00,
            "medicare": 6000.00,
            "futa": 6000.00,
            "suta": 6000.00,
        },
        "allocations": [
            {"department": "Engineering", "project": "Integrations", "hours": 120, "wages": 4500.00},
            {"department": "Product", "project": "Strategy", "hours": 40, "wages": 1500.00},
        ],
    },
    {
        "employee_id": "E003",
        "employee_name": "Morgan Lee",
        "pay_date": date(2024, 7, 15),
        "gross_pay": 2800.00,
        "net_pay": 2150.00,
        "taxes": 480.00,
        "deductions": 170.00,
        "hours": 80,
        "department": "Support",
        "project": "Customer Success",
        "pay_schedule": "Biweekly",
        "earnings": [
            {"type": "Regular", "hours": 80, "amount": 2700.00},
            {"type": "Shift Diff", "hours": 0, "amount": 100.00},
        ],
        "deductions_detail": [
            {"type": "Medical", "amount": 120.00},
            {"type": "Dental", "amount": 50.00},
        ],
        "contributions_detail": [
            {"type": "Wellness", "amount": 60.00},
        ],
        "employee_taxes": {"fit": 260.00, "ss": 173.00, "medicare": 47.00},
        "employer_taxes": {"fit": 40.00, "ss": 173.00, "medicare": 47.00, "futa": 28.00, "suta": 56.00},
        "taxable_wages": {
            "fit": 2800.00,
            "ss": 2800.00,
            "medicare": 2800.00,
            "futa": 2800.00,
            "suta": 2800.00,
        },
        "allocations": [
            {"department": "Support", "project": "Customer Success", "hours": 80, "wages": 2800.00},
        ],
    },
]
