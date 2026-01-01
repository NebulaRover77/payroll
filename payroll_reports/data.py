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
        "pay_date": date(2024, 7, 12),
        "gross_pay": 4200.00,
        "net_pay": 3200.00,
        "taxes": 750.00,
        "deductions": 250.00,
        "hours": 80,
        "department": "Engineering",
        "project": "Timekeeping",
        "pay_schedule": "Biweekly",
        "allocations": [
            {"department": "Engineering", "project": "Timekeeping", "hours": 60, "wages": 3150.00},
            {"department": "Engineering", "project": "Platform", "hours": 20, "wages": 1050.00},
        ],
    },
    {
        "employee_id": "E001",
        "pay_date": date(2024, 7, 26),
        "gross_pay": 4250.00,
        "net_pay": 3250.00,
        "taxes": 760.00,
        "deductions": 240.00,
        "hours": 80,
        "department": "Engineering",
        "project": "Timekeeping",
        "pay_schedule": "Biweekly",
        "allocations": [
            {"department": "Engineering", "project": "Timekeeping", "hours": 50, "wages": 2650.00},
            {"department": "Engineering", "project": "Integrations", "hours": 30, "wages": 1600.00},
        ],
    },
    {
        "employee_id": "E002",
        "pay_date": date(2024, 7, 31),
        "gross_pay": 6000.00,
        "net_pay": 4400.00,
        "taxes": 1200.00,
        "deductions": 400.00,
        "hours": 160,
        "department": "Engineering",
        "project": "Integrations",
        "pay_schedule": "Monthly",
        "allocations": [
            {"department": "Engineering", "project": "Integrations", "hours": 120, "wages": 4500.00},
            {"department": "Product", "project": "Strategy", "hours": 40, "wages": 1500.00},
        ],
    },
    {
        "employee_id": "E003",
        "pay_date": date(2024, 7, 15),
        "gross_pay": 2800.00,
        "net_pay": 2150.00,
        "taxes": 480.00,
        "deductions": 170.00,
        "hours": 80,
        "department": "Support",
        "project": "Customer Success",
        "pay_schedule": "Biweekly",
        "allocations": [
            {"department": "Support", "project": "Customer Success", "hours": 80, "wages": 2800.00},
        ],
    },
]
