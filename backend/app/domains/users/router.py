from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.core.logging import get_logger

router = APIRouter(prefix="/users", tags=["users"])
logger = get_logger(__name__)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["admin", "payroll", "people_ops", "viewer"] = "viewer"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: Literal["admin", "payroll", "people_ops", "viewer"]
    created_at: datetime


def _hash_password(raw: str) -> str:
    return sha256(raw.encode("utf-8")).hexdigest()


_USERS: list[dict[str, str | datetime]] = [
    {
        "id": str(uuid4()),
        "email": "admin@example.com",
        "hashed_password": _hash_password("dev"),
        "role": "admin",
        "created_at": datetime.utcnow(),
    },
    {
        "id": str(uuid4()),
        "email": "payroll@example.com",
        "hashed_password": _hash_password("dev"),
        "role": "payroll",
        "created_at": datetime.utcnow(),
    },
]


def _sanitize(user: dict[str, str | datetime]) -> UserOut:
    return UserOut(
        id=str(user["id"]),
        email=str(user["email"]),
        role=user["role"],
        created_at=user["created_at"],
    )


@router.get("", response_model=list[UserOut])
def list_users() -> list[UserOut]:
    return [_sanitize(user) for user in _USERS]


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate) -> UserOut:
    if any(u for u in _USERS if str(u["email"]).lower() == payload.email.lower()):
        raise HTTPException(status_code=400, detail="User already exists")

    user = {
        "id": str(uuid4()),
        "email": payload.email,
        "hashed_password": _hash_password(payload.password),
        "role": payload.role,
        "created_at": datetime.utcnow(),
    }

    _USERS.append(user)
    logger.info("user_created", email=payload.email, role=payload.role)
    return _sanitize(user)
