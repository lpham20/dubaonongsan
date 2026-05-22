from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import logging
import time

import requests
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_cache
from app.ingestion.input_price_records import InputPriceObservation, InputPriceScrapeResult
from app.ingestion.input_price_registry import build_input_price_scrapers
from app.models import AgriInputPriceObservation, AgriInputProduct, ScrapeRun


logger = logging.getLogger(__name__)
INPUT_PRICE_SCRAPE_ATTEMPTS = 2
INPUT_PRICE_RETRY_DELAY_SECONDS = 2.0


class InputPriceIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def scrape_and_store(self, source: str | None = None) -> list[dict]:
        summaries = []
        for scraper in build_input_price_scrapers(source):
            started_at = datetime.now(UTC)
            observations: list[InputPriceObservation] = []
            failed_summary: dict | None = None
            run = ScrapeRun(
                source=f"input:{scraper.source}",
                source_url=scraper.source_url,
                started_at=started_at,
                status="đang chạy",
            )
            self.db.add(run)
            self.db.commit()
            try:
                result = None
                last_error: Exception | None = None
                for attempt in range(1, INPUT_PRICE_SCRAPE_ATTEMPTS + 1):
                    logger.info("Starting input-price scrape: %s attempt=%d", scraper.source, attempt)
                    try:
                        candidate = scraper.scrape()
                    except Exception as exc:
                        last_error = exc
                        if attempt < INPUT_PRICE_SCRAPE_ATTEMPTS:
                            logger.warning(
                                "Input-price scrape attempt failed, retrying: %s attempt=%d error=%s",
                                scraper.source,
                                attempt,
                                exc,
                            )
                            time.sleep(INPUT_PRICE_RETRY_DELAY_SECONDS)
                            continue
                        raise
                    if candidate.observations or attempt >= INPUT_PRICE_SCRAPE_ATTEMPTS:
                        result = candidate
                        break
                    logger.warning("Input-price scrape returned 0 records, retrying: %s attempt=%d", scraper.source, attempt)
                    time.sleep(INPUT_PRICE_RETRY_DELAY_SECONDS)
                if result is None:
                    raise last_error or RuntimeError(f"Input-price scrape did not return a result: {scraper.source}")
                inserted, updated = self.store(result)
                observations = result.observations
                run.status = "thành công"
                run.records_found = len(result.observations)
                run.records_inserted = inserted
                run.records_updated = updated
                if len(result.observations) == 0:
                    run.status = "trống"
                    run.error_message = "Parser tìm 0 dữ liệu giá phân bón."
                    logger.warning("Input-price scrape returned 0 records: %s", scraper.source)
                if inserted == 0 and updated == 0 and len(result.observations) > 0:
                    run.status = "trùng lặp"
                    run.error_message = "Tất cả dữ liệu giá phân bón trùng với DB."
                    logger.info("Input-price scrape parsed %d records but none persisted: %s", len(result.observations), scraper.source)
                logger.info(
                    "Input-price scrape success: %s found=%d inserted=%d updated=%d",
                    scraper.source,
                    len(result.observations),
                    inserted,
                    updated,
                )
            except requests.Timeout as exc:
                logger.warning("Input-price scrape timeout: %s", scraper.source)
                self.db.rollback()
                run = self.db.get(ScrapeRun, run.id)
                if run:
                    run.status = "thất bại"
                    run.error_message = str(exc)
                failed_summary = {
                    "source": scraper.source,
                    "source_url": scraper.source_url,
                    "status": "thất bại",
                    "error": str(exc),
                }
            except Exception as exc:
                logger.exception("Input-price scrape failed: %s", scraper.source)
                self.db.rollback()
                run = self.db.get(ScrapeRun, run.id)
                if run:
                    run.status = "thất bại"
                    run.error_message = str(exc)
                failed_summary = {
                    "source": scraper.source,
                    "source_url": scraper.source_url,
                    "status": "thất bại",
                    "error": str(exc),
                }
            finally:
                if run:
                    run.finished_at = datetime.now(UTC)
                    self.db.add(run)
                    self.db.commit()
                    summaries.append(failed_summary or self._summary(run, observations))
        if summaries:
            invalidate_cache("input-price")
            invalidate_cache("llm-input-prices")
        return summaries

    def store(self, result: InputPriceScrapeResult) -> tuple[int, int]:
        inserted = 0
        updated = 0
        pending: dict[tuple, AgriInputPriceObservation] = {}
        for observation in result.observations:
            product = self._get_or_create_product(observation)
            key = (
                product.product_id,
                observation.observed_at,
                observation.province,
                observation.brand,
                observation.source,
                observation.package_size_kg,
            )
            normalized_price = round(observation.package_price_vnd / observation.package_size_kg, 2)
            if key in pending:
                existing = pending[key]
                _apply_observation(existing, observation, normalized_price)
                updated += 1
                continue

            existing = self.db.scalar(
                select(AgriInputPriceObservation).where(
                    and_(
                        AgriInputPriceObservation.product_id == product.product_id,
                        AgriInputPriceObservation.observed_at == observation.observed_at,
                        AgriInputPriceObservation.province == observation.province,
                        AgriInputPriceObservation.brand == observation.brand,
                        AgriInputPriceObservation.source_name == observation.source,
                        AgriInputPriceObservation.package_size_kg == observation.package_size_kg,
                    )
                )
            )
            if existing:
                _apply_observation(existing, observation, normalized_price)
                updated += 1
                continue

            row = AgriInputPriceObservation(
                product_id=product.product_id,
                observed_at=observation.observed_at,
                province=observation.province,
                region_name=observation.region_name,
                brand=observation.brand,
                seller_name=observation.seller_name,
                source_name=observation.source,
                source_url=observation.source_url,
                package_price_vnd=observation.package_price_vnd,
                normalized_price_vnd=normalized_price,
                normalized_unit="kg",
                package_size_kg=observation.package_size_kg,
                confidence_score=observation.confidence_score,
                data_kind=observation.data_kind,
                created_at=datetime.now(UTC),
            )
            self.db.add(row)
            pending[key] = row
            inserted += 1
        self.db.commit()
        return inserted, updated

    def latest_runs(self, limit: int = 20) -> list[dict]:
        rows = self.db.scalars(
            select(ScrapeRun)
            .where(ScrapeRun.source.like("input:%"))
            .order_by(desc(ScrapeRun.started_at))
            .limit(limit)
        ).all()
        return [self._run_to_dict(row) for row in rows]

    def _get_or_create_product(self, observation: InputPriceObservation) -> AgriInputProduct:
        product = self.db.scalar(select(AgriInputProduct).where(AgriInputProduct.slug == observation.product_slug))
        package_label = f"Bao {observation.package_size_kg:g} kg"
        if product:
            product.category = "fertilizer"
            product.product_type = product.product_type or observation.product_type
            product.nutrient_profile = product.nutrient_profile or observation.nutrient_profile
            product.package_size_kg = product.package_size_kg or observation.package_size_kg
            product.package_label = product.package_label or package_label
            product.is_active = True
            return product
        product = AgriInputProduct(
            slug=observation.product_slug,
            name=observation.product_name,
            category="fertilizer",
            product_type=observation.product_type,
            nutrient_profile=observation.nutrient_profile,
            standard_unit="kg",
            package_label=package_label,
            package_size_kg=observation.package_size_kg,
            notes="Được phát hiện từ dữ liệu giá phân bón công khai.",
            is_active=True,
        )
        self.db.add(product)
        self.db.flush()
        return product

    def _summary(self, run: ScrapeRun, observations: list[InputPriceObservation]) -> dict:
        summary = self._run_to_dict(run)
        summary["sample"] = [asdict(item) for item in observations[:5]]
        return summary

    @staticmethod
    def _run_to_dict(run: ScrapeRun) -> dict:
        return {
            "id": run.id,
            "source": run.source,
            "source_url": run.source_url,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "status": run.status,
            "records_found": run.records_found,
            "records_inserted": run.records_inserted,
            "records_updated": run.records_updated,
            "error_message": run.error_message,
        }


def _apply_observation(
    row: AgriInputPriceObservation,
    observation: InputPriceObservation,
    normalized_price: float,
) -> None:
    row.region_name = observation.region_name
    row.seller_name = observation.seller_name
    row.source_url = observation.source_url
    row.package_price_vnd = observation.package_price_vnd
    row.normalized_price_vnd = normalized_price
    row.normalized_unit = "kg"
    row.package_size_kg = observation.package_size_kg
    row.confidence_score = observation.confidence_score
    row.data_kind = observation.data_kind
