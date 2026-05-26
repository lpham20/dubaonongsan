from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppUser, FeatureFlag


def is_feature_enabled(db: Session, flag_key: str, *, default: bool = False) -> bool:
    flag = db.get(FeatureFlag, _normalize_key(flag_key))
    return bool(flag.enabled) if flag is not None else default


def list_feature_flags(db: Session) -> list[FeatureFlag]:
    return db.scalars(select(FeatureFlag).order_by(FeatureFlag.flag_key)).all()


def set_feature_flag(
    db: Session,
    *,
    flag_key: str,
    enabled: bool,
    description: str | None = None,
    user: AppUser | None = None,
) -> FeatureFlag:
    key = _normalize_key(flag_key)
    flag = db.get(FeatureFlag, key)
    if flag is None:
        flag = FeatureFlag(flag_key=key)
    flag.enabled = bool(enabled)
    if description is not None:
        flag.description = description.strip()[:1000] or None
    flag.updated_at = datetime.now(UTC)
    flag.updated_by = user.user_id if user is not None else None
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


def _normalize_key(value: str) -> str:
    key = (value or "").strip().lower().replace(" ", "_")
    if not key:
        raise ValueError("Feature flag key is required")
    if len(key) > 120:
        raise ValueError("Feature flag key is too long")
    return key
