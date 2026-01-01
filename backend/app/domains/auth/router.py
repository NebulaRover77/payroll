from fastapi import APIRouter

from app.core.logging import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


@router.post("/login")
def login(email: str, password: str) -> dict[str, str]:
    logger.info("login_attempt", email=email)
    # Placeholder logic; integrate with identity provider later
    return {"access_token": "demo-token", "token_type": "bearer"}
