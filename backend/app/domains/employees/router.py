from datetime import date

from fastapi import APIRouter

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("")
def list_employees() -> list[dict[str, str | date]]:
    return [
        {"id": 1, "name": "Ada Lovelace", "hire_date": date(2020, 1, 1), "role": "Engineer"},
        {"id": 2, "name": "Grace Hopper", "hire_date": date(2021, 6, 15), "role": "Engineer"},
    ]
