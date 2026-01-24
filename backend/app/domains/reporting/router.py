from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reporting"])


@router.get("")
def list_reports() -> list[dict[str, str]]:
    return [
        {"id": 1, "name": "Payroll Summary", "status": "ready"},
        {"id": 2, "name": "Headcount", "status": "queued"},
        {"id": 3, "name": "Payroll Details", "status": "ready"},
        {"id": 4, "name": "Form 940", "status": "ready"},
        {"id": 5, "name": "Form 941", "status": "ready"},
        {"id": 6, "name": "Payroll Tax Liabilities", "status": "ready"},
        {"id": 7, "name": "Tax Deposits", "status": "ready"},
        {"id": 8, "name": "W-2 & W-3", "status": "ready"},
        {"id": 9, "name": "Electronic W-2 File", "status": "coming_soon"},
    ]
