from contextlib import asynccontextmanager
from datetime import UTC, datetime
import logging
import logging.config
import os
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.advisory import router as advisory_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.content import router as content_router
from app.api.fertilizer import router as fertilizer_router
from app.api.input_prices import router as input_prices_router
from app.api.llm_content import router as llm_content_router
from app.api.metadata import router as metadata_router
from app.api.ops import router as ops_router
from app.api.public import router as public_router
from app.api.roi import router as roi_router
from app.api.security import router as security_router
from app.api.world_fertilizer import router as world_fertilizer_router
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db import init_db
from app.models import AppUser
from app.seed import normalize_vietnamese_labels, seed_database
from app.services.auth import hash_password
from app.services.content_portal import ContentPortalService
from app.services.crop_catalog import ensure_crop_catalog
from app.services.input_prices import seed_input_prices
from app.services.platform_jobs import JobScheduler


settings = get_settings()
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "format": '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
            },
            "default": {"format": "%(asctime)s %(levelname)s [%(name)s] %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if settings.environment == "production" else "default",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO" if settings.environment == "production" else "DEBUG",
        },
    }
)
logger = logging.getLogger("marketai")
API_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


def _ensure_demo_user(db: Session) -> None:
    if not settings.create_demo_user:
        return
    email = "demo@marketai.vn"
    existing = db.scalar(select(AppUser).where(AppUser.email == email))
    if existing:
        if existing.display_name == "Demo":
            existing.display_name = "Tài khoản thử"
            db.commit()
        return
    demo_password = os.getenv("MARKETAI_DEMO_PASSWORD")
    if not demo_password or len(demo_password) < 16:
        raise RuntimeError("MARKETAI_DEMO_PASSWORD phải có ít nhất 16 ký tự khi bật MARKETAI_CREATE_DEMO_USER")
    if len(set(demo_password)) < 6:
        raise RuntimeError("MARKETAI_DEMO_PASSWORD quá đơn giản")
    weak_patterns = ("12345", "password", "qwerty", "abcdef", "demo")
    if any(pattern in demo_password.lower() for pattern in weak_patterns):
        raise RuntimeError("MARKETAI_DEMO_PASSWORD chứa pattern yếu")
    db.add(
        AppUser(
            email=email,
            display_name="Tài khoản thử",
            password_hash=hash_password(demo_password),
            created_at=datetime.now(UTC),
            is_admin=False,
        )
    )
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.seed_on_startup or settings.database_url == "sqlite:///:memory:":
        from app.db import SessionLocal

        with SessionLocal() as db:
            seed_database(db)
            normalize_vietnamese_labels(db)
            ensure_crop_catalog(db)
            seed_input_prices(db)
            _ensure_demo_user(db)
            ContentPortalService(db).seed_guides()
            ContentPortalService(db).seed_fallback_news()
    if settings.start_scheduler_in_api:
        JobScheduler.start_once()
    yield
    JobScheduler.shutdown()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
    max_age=3600,
)
app.include_router(auth_router)
app.include_router(content_router)
app.include_router(fertilizer_router)
app.include_router(input_prices_router)
app.include_router(metadata_router)
app.include_router(analytics_router)
app.include_router(public_router)
app.include_router(ops_router)
app.include_router(llm_content_router)
app.include_router(roi_router)
app.include_router(security_router)
app.include_router(world_fertilizer_router)
app.include_router(advisory_router)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    for name, value in API_SECURITY_HEADERS.items():
        if name not in response.headers:
            response.headers[name] = value
    if settings.environment == "production":
        if "Strict-Transport-Security" not in response.headers:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    safe_path = request.url.path.replace("\n", "\\n").replace("\r", "\\r")
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
        request.method,
        safe_path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
