from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("")
def list_payments() -> list[dict[str, str | float]]:
    return [
        {"id": 1, "employee_id": 1, "amount": 3000.00, "status": "sent"},
        {"id": 2, "employee_id": 2, "amount": 3200.00, "status": "pending"},
    ]
