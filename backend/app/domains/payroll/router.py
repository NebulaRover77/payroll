from datetime import date

from fastapi import APIRouter

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.get("")
def list_runs() -> list[dict[str, str | float]]:
    return [
        {"id": 1, "period_start": str(date(2024, 2, 1)), "period_end": str(date(2024, 2, 15)), "total_gross": 42000.00}
    ]
