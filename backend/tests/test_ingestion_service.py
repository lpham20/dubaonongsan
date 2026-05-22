import os
from datetime import UTC, datetime

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.ingestion.input_price_records import InputPriceObservation, InputPriceScrapeResult
from app.ingestion.input_price_service import InputPriceIngestionService
from app.ingestion.records import PriceObservation, ScrapeResult
from app.ingestion.service import PriceIngestionService
from app.models import AgriInputPriceObservation, DailyMarketPrice


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


def test_input_price_store_deduplicates_scraped_observations():
    init_db()
    observed_at = datetime(2026, 5, 20, tzinfo=UTC)
    duplicate = InputPriceObservation(
        observed_at=observed_at,
        product_slug="ure",
        product_name="Urê",
        product_type="Phân đơn",
        nutrient_profile="46% N",
        province="Miền Tây",
        region_name="Đồng bằng sông Cửu Long",
        brand="Cà Mau",
        seller_name="Phân Bón Việt Nga",
        source="vietnga.vn",
        source_url="https://vietnga.vn/gia-phan-bon-hom-nay/#date-732",
        package_price_vnd=960000,
        package_size_kg=50,
    )
    result = InputPriceScrapeResult(
        source="vietnga.vn",
        source_url="https://vietnga.vn/gia-phan-bon-hom-nay/",
        observations=[
            duplicate,
            InputPriceObservation(
                **{
                    **duplicate.__dict__,
                    "package_price_vnd": 970000,
                }
            ),
        ],
    )

    with SessionLocal() as db:
        inserted, updated = InputPriceIngestionService(db).store(result)
        rows = db.scalars(
            select(AgriInputPriceObservation).where(AgriInputPriceObservation.source_name == "vietnga.vn")
        ).all()

    assert inserted == 1
    assert updated == 1
    assert len(rows) == 1
    assert float(rows[0].package_price_vnd) == 970000
    assert float(rows[0].normalized_price_vnd) == 19400
    assert rows[0].data_kind == "scraped"
