from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.job_status import STATUS_FAILED
from app.core.logging import JsonLogFormatter
from app.db import Base
from app.models import DailyMarketPrice, DurianVariety, FeatureFlag, MlModelVersion, ModelReadyBackfillCheckpoint, ProductionRegion, RecommendationSession
from app.services.feature_flags import is_feature_enabled, list_feature_flags, set_feature_flag
from app.services.ml_model_versions import record_crop_model_version
from app.services.model_ready_backfill import MODEL_READY_GRADE, ModelReadyBackfillService, market_day_start
from app.services.platform_jobs import PlatformJobService
from app.services.public_price_calibration import PublicPriceCalibrationService
from app.services.world_fertilizer import WorldFertilizerIngestionService


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
            record_timestamp=market_day_start() - timedelta(days=5),
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

    assert first["records_inserted"] == 3
    assert first["checkpoint_skipped"] == 0
    assert second["records_inserted"] == 0
    assert second["checkpoint_skipped"] == 1
    latest = db.scalar(select(DailyMarketPrice.record_timestamp).order_by(DailyMarketPrice.record_timestamp.desc()).limit(1))
    assert latest == market_day_start()
    assert db.scalar(select(ModelReadyBackfillCheckpoint).where(ModelReadyBackfillCheckpoint.crop_type == "sau_rieng")) is not None


def test_public_price_calibration_window_advances_past_stale_crop_rows():
    db = _session()
    region = ProductionRegion(region_name="tay nguyen", province="dak lak")
    variety = DurianVariety(name="Cà phê tổng hợp", crop_type="ca_phe")
    db.add_all([region, variety])
    db.flush()
    db.add(
        DailyMarketPrice(
            record_timestamp=market_day_start() - timedelta(days=5),
            variety_id=variety.variety_id,
            crop_type="ca_phe",
            quality_grade=MODEL_READY_GRADE,
            region_id=region.region_id,
            exchange_source="manual",
            min_price_vnd=95000,
            max_price_vnd=96000,
            volume_traded_tons=10,
        )
    )
    db.commit()

    dates = PublicPriceCalibrationService(db, crop_type="ca_phe", days=3)._date_window()

    assert dates[-1] == market_day_start()


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


def test_failed_platform_job_sends_ops_alert(monkeypatch):
    db = _session()
    alerts: list[tuple[str, dict]] = []
    monkeypatch.setattr("app.services.platform_jobs.send_ops_alert", lambda event, payload: alerts.append((event, payload)) or True)

    service = PlatformJobService(db)
    job = service._start_job("unit_failure")
    service._finish_job(job, STATUS_FAILED, {"source": "unit"}, "boom")

    assert len(alerts) == 1
    event, payload = alerts[0]
    assert event == "platform_job_failed"
    assert payload["job_id"] == job.job_id
    assert payload["job_name"] == "unit_failure"
    assert payload["status"] == STATUS_FAILED
    assert payload["error_message"] == "boom"
    assert payload["summary"] == {"source": "unit"}
    assert payload["duration_seconds"] >= 0


def test_world_fertilizer_scraper_failure_sends_source_alert(monkeypatch):
    import app.services.world_fertilizer as world_fertilizer

    db = _session()
    alerts: list[tuple[str, dict]] = []

    class BrokenScraper:
        source = "commoditypriceapi_urea_public_1y"
        source_url = "https://commoditypriceapi.example.test/tools/urea/prices"

        @staticmethod
        def scrape():
            raise ValueError("Next action id changed")

    monkeypatch.setattr(world_fertilizer, "WORLD_FERTILIZER_SCRAPE_ATTEMPTS", 1)
    monkeypatch.setattr(world_fertilizer, "WORLD_FERTILIZER_RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(world_fertilizer, "build_world_fertilizer_scrapers", lambda source=None: [BrokenScraper()])
    monkeypatch.setattr(world_fertilizer, "send_ops_alert", lambda event, payload: alerts.append((event, payload)) or True)

    result = WorldFertilizerIngestionService(db).scrape_and_store(source="commoditypriceapi_urea_public_1y")

    assert result[0]["status"] == STATUS_FAILED
    assert len(alerts) == 1
    event, payload = alerts[0]
    assert event == "world_fertilizer_scrape_failed"
    assert payload["source"] == "commoditypriceapi_urea_public_1y"
    assert payload["status"] == STATUS_FAILED
    assert "Next action id changed" in payload["error_message"]


def test_json_log_formatter_keeps_valid_json_with_extra_fields():
    record = logging.LogRecord(
        name="marketai.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='request "%s" completed',
        args=("abc",),
        exc_info=None,
    )
    record.request_id = "rid-123"
    record.duration_ms = 12.34

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["msg"] == 'request "abc" completed'
    assert payload["logger"] == "marketai.test"
    assert payload["request_id"] == "rid-123"
    assert payload["duration_ms"] == 12.34
