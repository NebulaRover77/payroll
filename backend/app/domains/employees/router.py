from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.employee import Employee

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
    id: int


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_session)):
    rows = db.query(Employee).order_by(Employee.name.asc(), Employee.id.asc()).all()
    return [
        EmployeeOut(
            id=r.id,
            name=r.name,
            role=r.role,
            type=r.pay_type,
            rate=float(r.rate or 0),
            defaultHours=float(r.default_hours or 0),
            status=r.status,
            tax=r.tax,
            hire_date=r.hire_date,
        )
        for r in rows
    ]


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_session)):
    row = Employee(
        name=payload.name.strip(),
        role=payload.role,
        pay_type=payload.type,
        rate=payload.rate,
        default_hours=payload.defaultHours,
        status=payload.status,
        tax=payload.tax,
        hire_date=payload.hire_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return EmployeeOut(
        id=row.id,
        **payload.model_dump(),
    )


@router.delete("/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Session = Depends(get_session)):
    row = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(row)
    db.commit()
    return None
