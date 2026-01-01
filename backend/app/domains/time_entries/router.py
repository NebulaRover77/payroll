from datetime import date

from fastapi import APIRouter

router = APIRouter(prefix="/time", tags=["time"])


@router.get("")
def list_time_entries() -> list[dict[str, str | float | date]]:
    return [
        {"employee_id": 1, "date": date(2024, 3, 1), "hours": 8.0, "project_code": "PRJ-123"}
    ]
