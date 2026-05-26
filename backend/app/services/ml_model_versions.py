from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import MlModelVersion


def record_crop_model_version(db: Session, crop_type: str, metrics: dict[str, Any] | None = None) -> MlModelVersion | None:
    key = crop_type.strip().lower().replace("-", "_")
    artifacts_dir = Path(get_settings().ml_artifacts)
    return _record_artifact(
        db,
        model_key=f"crop:{key}",
        model_kind="crop-lstm-tflite",
        artifact_path=artifacts_dir / f"lstm_{key}.tflite",
        metadata_path=artifacts_dir / f"lstm_{key}.meta.json",
        crop_type=key,
        commodity_slug=None,
        metrics=metrics,
    )


def record_world_fertilizer_model_version(
    db: Session,
    commodity_slug: str,
    metrics: dict[str, Any] | None = None,
) -> MlModelVersion | None:
    key = commodity_slug.strip().lower().replace("-", "_")
    artifacts_dir = Path(get_settings().ml_artifacts)
    return _record_artifact(
        db,
        model_key=f"world-fertilizer:{key}",
        model_kind="world-fertilizer-lstm-tflite",
        artifact_path=artifacts_dir / f"world_lstm_{key}.tflite",
        metadata_path=artifacts_dir / f"world_lstm_{key}.meta.json",
        crop_type=None,
        commodity_slug=key,
        metrics=metrics,
    )


def list_model_versions(db: Session, limit: int = 50) -> list[MlModelVersion]:
    return db.scalars(
        select(MlModelVersion)
        .order_by(MlModelVersion.created_at.desc(), MlModelVersion.version_id.desc())
        .limit(max(1, min(limit, 200)))
    ).all()


def _record_artifact(
    db: Session,
    *,
    model_key: str,
    model_kind: str,
    artifact_path: Path,
    metadata_path: Path,
    crop_type: str | None,
    commodity_slug: str | None,
    metrics: dict[str, Any] | None,
) -> MlModelVersion | None:
    if not artifact_path.exists():
        return None
    digest = _sha256_file(artifact_path)
    existing = db.scalar(
        select(MlModelVersion).where(
            MlModelVersion.model_key == model_key,
            MlModelVersion.artifact_sha256 == digest,
        )
    )
    now = datetime.now(UTC)
    if existing is not None:
        existing.metrics_json = metrics or existing.metrics_json
        existing.is_active = True
        existing.activated_at = now
        db.add(existing)
        _deactivate_other_versions(db, model_key=model_key, active_sha=digest)
        db.commit()
        db.refresh(existing)
        return existing

    metadata = _read_json(metadata_path)
    row = MlModelVersion(
        model_key=model_key,
        model_kind=str(metadata.get("model_kind") or model_kind),
        crop_type=crop_type,
        commodity_slug=commodity_slug,
        artifact_path=str(artifact_path),
        artifact_sha256=digest,
        metadata_json=metadata,
        metrics_json=metrics,
        is_active=True,
        created_at=now,
        activated_at=now,
    )
    db.add(row)
    _deactivate_other_versions(db, model_key=model_key, active_sha=digest)
    db.commit()
    db.refresh(row)
    return row


def _deactivate_other_versions(db: Session, *, model_key: str, active_sha: str) -> None:
    db.execute(
        update(MlModelVersion)
        .where(MlModelVersion.model_key == model_key, MlModelVersion.artifact_sha256 != active_sha)
        .values(is_active=False)
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
