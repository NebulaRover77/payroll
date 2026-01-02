from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.monitoring import configure_error_monitoring
from app.core.observability import configure_observability
from app.domains.auth.router import router as auth_router
from app.domains.employees.router import router as employee_router
from app.domains.payments.router import router as payments_router
from app.domains.payroll.router import router as payroll_router
from app.domains.reporting.router import router as reporting_router
from app.domains.time_entries.router import router as time_router
from app.domains.users.router import router as users_router

configure_logging(settings.log_level)
configure_observability()
configure_error_monitoring()
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.cors_origins] or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(time_router)
app.include_router(payroll_router)
app.include_router(payments_router)
app.include_router(reporting_router)
app.include_router(users_router)


@app.on_event("startup")
def startup_event() -> None:
    logger.info("startup_complete", env=settings.env)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Payroll API running", "environment": settings.env}
