from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppUser, RecommendationSession, YieldFeedback

_SESSION_CODE_RE = re.compile(r"^[0-9a-f]{8}$")
_SESSION_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def log_recommendation_session(
    db: Session,
    *,
    user: AppUser,
    request: Request,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> RecommendationSession:
    now = datetime.now(UTC)
    session_id = _new_unique_session_id(db)
    annual = result.get("recommendation", {}).get("annual_total", {})
    confidence = result.get("confidence", {})
    soil = payload.get("soil") or {}
    location = payload.get("location") or {}
    session = RecommendationSession(
        session_id=session_id,
        user_id=user.user_id,
        crop=payload.get("crop"),
        variety=payload.get("variety"),
        growth_stage=payload.get("growth_stage"),
        province=location.get("province"),
        soil_texture=soil.get("texture"),
        yield_target_t_ha=payload.get("yield_target_t_ha"),
        tree_density_per_ha=payload.get("tree_density_per_ha"),
        annual_n_kg_ha=annual.get("n_kg_ha"),
        annual_p2o5_kg_ha=annual.get("p2o5_kg_ha"),
        annual_k2o_kg_ha=annual.get("k2o_kg_ha"),
        confidence_tier=confidence.get("calibration_tier") or confidence.get("overall"),
        confidence_score=confidence.get("score") or confidence.get("data_quality_score"),
        engine_version=result.get("engine_version"),
        knowledge_base_version=result.get("knowledge_base_version"),
        request_json=payload,
        response_json=result,
        ip_address=None,
        user_agent=request.headers.get("user-agent", "")[:500] or None,
        created_at=now,
        created_date=now.date(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _new_unique_session_id(db: Session, attempts: int = 8) -> str:
    for _ in range(attempts):
        session_id = str(uuid4())
        prefix = session_id[:8]
        collision = db.scalar(select(RecommendationSession.session_id).where(RecommendationSession.session_id.like(f"{prefix}%")).limit(1))
        if collision is None:
            return session_id
    raise RuntimeError("Could not allocate a unique recommendation session code")


def save_yield_feedback(
    db: Session,
    *,
    session_code: str,
    user: AppUser,
    actual_yield_t_ha: float,
    harvest_date: Any = None,
    fertilizer_followed_pct: float | None = None,
    rating: int | None = None,
    note: str | None = None,
    contact_phone: str | None = None,
) -> YieldFeedback:
    session = _resolve_session(db, session_code)
    if session is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã khuyến nghị. Vui lòng kiểm tra lại 8 ký tự đầu.")

    if session.user_id != user.user_id and not bool(user.is_admin):
        raise HTTPException(status_code=403, detail="Ban khong co quyen bao cao cho ma phien nay.")

    feedback = db.scalar(select(YieldFeedback).where(YieldFeedback.session_id == session.session_id))
    if feedback is None:
        feedback = YieldFeedback(
            session_id=session.session_id,
            crop=session.crop,
            variety=session.variety,
            created_at=datetime.now(UTC),
        )
    feedback.actual_yield_t_ha = actual_yield_t_ha
    feedback.harvest_date = harvest_date
    feedback.fertilizer_followed_pct = fertilizer_followed_pct
    feedback.rating = rating
    feedback.note = note
    feedback.contact_phone = contact_phone
    feedback.yield_unit = "t_ha"
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def _resolve_session(db: Session, session_code: str) -> RecommendationSession | None:
    clean = (session_code or "").strip().lower()
    if not clean:
        return None
    if _SESSION_CODE_RE.fullmatch(clean):
        return db.scalar(
            select(RecommendationSession)
            .where(RecommendationSession.session_id.like(f"{clean}%"))
            .order_by(RecommendationSession.created_at.desc())
        )
    if _SESSION_ID_RE.fullmatch(clean):
        return db.get(RecommendationSession, clean)
    return None
