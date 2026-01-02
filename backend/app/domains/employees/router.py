from datetime import date
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/employees", tags=["employees"])


class EmployeeBase(BaseModel):
    name: str
    role: str = "—"
    type: Literal["hourly", "salary"] = "salary"
    rate: float = 0
    defaultHours: float = 0
    status: Literal["active", "on_leave", "terminated"] = "active"
    tax: Literal["standard", "low", "high"] = "standard"
    hire_date: date | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeOut(EmployeeBase):
    id: str


_EMPLOYEES: list[EmployeeOut] = [
    EmployeeOut(
        id=str(uuid4()),
        name="Alex Chen",
        role="Payroll Analyst",
        type="salary",
        rate=3600,
        defaultHours=80,
        status="active",
        tax="standard",
    ),
    EmployeeOut(
        id=str(uuid4()),
        name="Priya Patel",
        role="Support Lead",
        type="hourly",
        rate=38,
        defaultHours=80,
        status="active",
        tax="low",
    ),
    EmployeeOut(
        id=str(uuid4()),
        name="Marcos Diaz",
        role="Implementation",
        type="hourly",
        rate=42,
        defaultHours=60,
        status="on_leave",
        tax="standard",
    ),
]


@router.get("", response_model=list[EmployeeOut])
def list_employees():
    return _EMPLOYEES


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate):
    emp = EmployeeOut(id=str(uuid4()), **payload.model_dump())
    _EMPLOYEES.append(emp)
    return emp


@router.delete("/{employee_id}", status_code=204)
def delete_employee(employee_id: str):
    idx = next((i for i, e in enumerate(_EMPLOYEES) if e.id == employee_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    _EMPLOYEES.pop(idx)
    return None
