import os
from datetime import UTC, datetime

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.ingestion.records import PriceObservation, ScrapeResult
from app.ingestion.service import PriceIngestionService
from app.models import DailyMarketPrice


def test_store_deduplicates_observations_with_same_unique_key():
    init_db()
    observed_at = datetime(2026, 5, 4, tzinfo=UTC)
    duplicate = PriceObservation(
        observed_at=observed_at,
        variety_name="Ri6 test duplicate",
        quality_grade="Tong hop",
        region_name="Test region",
        province="Dong Thap",
        source="test-source-duplicate",
        source_url="https://example.test/prices",
        min_price_vnd=60000,
        max_price_vnd=90000,
        crop_type="sau_rieng",
    )
    result = ScrapeResult(
        source="test-source-duplicate",
        source_url="https://example.test/prices",
        observations=[
            duplicate,
            PriceObservation(
                **{
                    **duplicate.__dict__,
                    "min_price_vnd": 61000,
                    "max_price_vnd": 91000,
                }
            ),
        ],
    )

    with SessionLocal() as db:
        inserted, updated = PriceIngestionService(db).store(result)
        rows = db.scalars(
            select(DailyMarketPrice).where(DailyMarketPrice.exchange_source == "test-source-duplicate")
        ).all()

    assert inserted == 1
    assert updated == 1
    assert len(rows) == 1
    assert float(rows[0].max_price_vnd) == 91000
