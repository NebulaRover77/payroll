from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_session
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])
logger = get_logger(__name__)


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    role: Literal["admin", "payroll", "people_ops", "viewer"] = "viewer"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip()
        if "@" not in email:
            raise ValueError("Invalid email format")
        return email


class UserOut(BaseModel):
    id: int
    email: str
    role: Literal["admin", "payroll", "people_ops", "viewer"]
    created_at: datetime


def _hash_password(raw: str) -> str:
    return sha256(raw.encode("utf-8")).hexdigest()


def _sanitize(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at=user.created_at or datetime.utcnow(),
    )


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_session)) -> list[UserOut]:
    users = db.query(User).order_by(User.created_at.desc(), User.id.desc()).all()
    return [_sanitize(user) for user in users]


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> UserOut:
    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == payload.email.lower())
        .one_or_none()
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=payload.email.strip(),
        hashed_password=_hash_password(payload.password),
        role=payload.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("user_created", email=payload.email, role=payload.role)
    return _sanitize(user)
