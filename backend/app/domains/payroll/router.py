from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.payroll_run import PayrollRun

router = APIRouter(prefix="/payroll", tags=["payroll"])


class PayrollRunOut(BaseModel):
    id: int
    period_start: date
    period_end: date
    total_gross: float
    status: str
    void_reason: str | None = None
    voided_at: datetime | None = None


class VoidPayrollRunRequest(BaseModel):
    reason: Annotated[str, Field(min_length=3, max_length=255)]


@router.get("", response_model=list[PayrollRunOut])
def list_runs(db: Session = Depends(get_session)) -> list[PayrollRunOut]:
    rows = db.query(PayrollRun).order_by(PayrollRun.period_start.desc(), PayrollRun.id.desc()).all()
    return [
        PayrollRunOut(
            id=row.id,
            period_start=row.period_start,
            period_end=row.period_end,
            total_gross=float(row.total_gross),
            status=row.status,
            void_reason=row.void_reason,
            voided_at=row.voided_at,
        )
        for row in rows
    ]


@router.post("/{run_id}/void", response_model=PayrollRunOut)
def void_run(run_id: int, payload: VoidPayrollRunRequest, db: Session = Depends(get_session)):
    run = db.query(PayrollRun).filter(PayrollRun.id == run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    if run.status == "voided":
        raise HTTPException(status_code=409, detail="Payroll run already voided")

    run.status = "voided"
    run.void_reason = payload.reason.strip()
    run.voided_at = datetime.utcnow()
    db.commit()
    db.refresh(run)

    return PayrollRunOut(
        id=run.id,
        period_start=run.period_start,
        period_end=run.period_end,
        total_gross=float(run.total_gross),
        status=run.status,
        void_reason=run.void_reason,
        voided_at=run.voided_at,
    )
