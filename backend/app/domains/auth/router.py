from __future__ import annotations

import secrets
from hashlib import sha256
from hmac import compare_digest

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_session
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip()
        if "@" not in email:
            raise ValueError("Invalid email")
        return email


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str


def _hash_password(raw: str) -> str:
    return sha256(raw.encode("utf-8")).hexdigest()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_session)) -> LoginResponse:
    logger.info("login_attempt", email=payload.email)
    user = (
        db.query(User)
        .filter(func.lower(User.email) == payload.email.lower())
        .one_or_none()
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not compare_digest(user.hashed_password, _hash_password(payload.password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = secrets.token_urlsafe(32)
    logger.info("login_success", email=payload.email, role=user.role)

    return LoginResponse(access_token=token, email=user.email, role=user.role)
