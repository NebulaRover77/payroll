import sentry_sdk

from app.core.config import settings


def configure_error_monitoring() -> None:
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.env, traces_sample_rate=0.2)
