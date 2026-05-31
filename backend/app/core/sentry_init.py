from __future__ import annotations

import logging
import os
from typing import Any


logger = logging.getLogger(__name__)
_initialized = False


def init_sentry() -> None:
    """Initialize Sentry once for API and worker processes."""
    global _initialized
    if _initialized:
        return

    dsn = (
        os.getenv("MARKETAI_SENTRY_DSN", "").strip()
        or os.getenv("SENTRY_DSN_BACKEND", "").strip()
        or os.getenv("SENTRY_DSN", "").strip()
    )
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except Exception:
        logger.exception("sentry_import_failed")
        return

    if getattr(sentry_sdk, "is_initialized", lambda: False)():
        _initialized = True
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("MARKETAI_ENVIRONMENT", "production"),
        release=os.getenv("MARKETAI_RELEASE", "unknown"),
        traces_sample_rate=_bounded_sample_rate("MARKETAI_SENTRY_TRACES_SAMPLE_RATE", 0.1),
        profiles_sample_rate=_bounded_sample_rate("MARKETAI_SENTRY_PROFILES_SAMPLE_RATE", 0.1),
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(level=None, event_level=None),
        ],
        send_default_pii=False,
        before_send=_before_send_filter,
    )
    _initialized = True


def _bounded_sample_rate(env_name: str, default: float) -> float:
    raw = os.getenv(env_name, "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        value = default
    return max(0.0, min(value, 0.1))


def _before_send_filter(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    exc_info = hint.get("exc_info")
    if not exc_info:
        return event

    exc_type, exc_value, _ = exc_info
    try:
        from fastapi import HTTPException
        from starlette.exceptions import HTTPException as StarletteHTTPException
    except Exception:
        HTTPException = None  # type: ignore[assignment]
        StarletteHTTPException = None  # type: ignore[assignment]

    if HTTPException and isinstance(exc_value, HTTPException) and 400 <= exc_value.status_code < 500:
        return None
    if StarletteHTTPException and isinstance(exc_value, StarletteHTTPException) and 400 <= exc_value.status_code < 500:
        return None

    message = str(exc_value).lower()
    if exc_type.__name__ == "ValueError" and "parser" in message:
        return None
    if "aborterror" in message:
        return None
    return event
