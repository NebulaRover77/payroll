from fastapi import APIRouter, HTTPException, status

from app.core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/login")
def login(email: str, password: str) -> dict[str, str]:
    logger.info("login_attempt", email=email)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication is not configured.",
    )
