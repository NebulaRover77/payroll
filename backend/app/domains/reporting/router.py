from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reporting"])


@router.get("")
def list_reports() -> list[dict[str, str]]:
    return [
        {"id": 1, "name": "Payroll Summary", "status": "ready"},
        {"id": 2, "name": "Headcount", "status": "queued"},
    ]
