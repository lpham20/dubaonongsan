from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.models import DailyMarketPrice, DurianVariety, FeatureFlag, MlModelVersion, ModelReadyBackfillCheckpoint, ProductionRegion, RecommendationSession
from app.services.feature_flags import is_feature_enabled, list_feature_flags, set_feature_flag
from app.services.ml_model_versions import record_crop_model_version
from app.services.model_ready_backfill import MODEL_READY_GRADE, ModelReadyBackfillService
from app.services.platform_jobs import PlatformJobService


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_model_ready_backfill_uses_checkpoint_on_second_run():
    db = _session()
    region = ProductionRegion(region_name="tay nguyen", province="dak lak")
    variety = DurianVariety(name="Ri6", crop_type="sau_rieng")
    db.add_all([region, variety])
    db.flush()
    db.add(
        DailyMarketPrice(
            record_timestamp=datetime(2026, 5, 24),
            variety_id=variety.variety_id,
            crop_type="sau_rieng",
            quality_grade=MODEL_READY_GRADE,
            region_id=region.region_id,
            exchange_source="manual",
            min_price_vnd=60000,
            max_price_vnd=65000,
            volume_traded_tons=10,
        )
    )
    db.commit()

    first = ModelReadyBackfillService(db, days=3, crop_type="sau_rieng").backfill()
    second = ModelReadyBackfillService(db, days=3, crop_type="sau_rieng").backfill()

    assert first["records_inserted"] == 2
    assert first["checkpoint_skipped"] == 0
    assert second["records_inserted"] == 0
    assert second["checkpoint_skipped"] == 1
    assert db.scalar(select(ModelReadyBackfillCheckpoint).where(ModelReadyBackfillCheckpoint.crop_type == "sau_rieng")) is not None


def test_feature_flags_default_set_and_list():
    db = _session()

    assert is_feature_enabled(db, "new advisory panel", default=True) is True
    flag = set_feature_flag(db, flag_key="new advisory panel", enabled=False, description="Roll out slowly")

    assert flag.flag_key == "new_advisory_panel"
    assert is_feature_enabled(db, "new_advisory_panel", default=True) is False
    assert [item.flag_key for item in list_feature_flags(db)] == ["new_advisory_panel"]
    assert db.get(FeatureFlag, "new_advisory_panel") is not None


def test_model_version_registry_tracks_active_artifact(monkeypatch, tmp_path):
    db = _session()
    monkeypatch.setattr(
        "app.services.ml_model_versions.get_settings",
        lambda: SimpleNamespace(ml_artifacts=str(tmp_path)),
    )
    artifact = tmp_path / "lstm_sau_rieng.tflite"
    artifact.write_bytes(b"version-one")
    (tmp_path / "lstm_sau_rieng.meta.json").write_text('{"model_kind":"crop-lstm-tflite","source":"unit-test"}', encoding="utf-8")

    first = record_crop_model_version(db, "sau_rieng", metrics={"mae": 1.0})
    artifact.write_bytes(b"version-two")
    second = record_crop_model_version(db, "sau_rieng", metrics={"mae": 0.8})

    rows = db.scalars(select(MlModelVersion).order_by(MlModelVersion.created_at)).all()
    assert first is not None
    assert second is not None
    assert len(rows) == 2
    assert sum(1 for row in rows if row.is_active) == 1
    assert rows[-1].artifact_sha256 == second.artifact_sha256
    assert rows[-1].metrics_json == {"mae": 0.8}


def test_privacy_cleanup_clears_old_recommendation_session_ips(monkeypatch, tmp_path):
    db = _session()
    monkeypatch.setenv("MARKETAI_JOB_LOCK_DIR", str(tmp_path / "locks"))
    old_session = RecommendationSession(
        session_id="old-session",
        crop="sau_rieng",
        ip_address="203.0.113.10",
        created_at=datetime.now(UTC) - timedelta(days=8),
    )
    fresh_session = RecommendationSession(
        session_id="fresh-session",
        crop="sau_rieng",
        ip_address="203.0.113.11",
        created_at=datetime.now(UTC),
    )
    db.add_all([old_session, fresh_session])
    db.commit()

    summary = PlatformJobService(db).run_privacy_cleanup()

    assert summary["recommendation_session_ips_cleared"] == 1
    assert db.get(RecommendationSession, "old-session").ip_address is None
    assert db.get(RecommendationSession, "fresh-session").ip_address == "203.0.113.11"
