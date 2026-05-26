from dataclasses import asdict
from datetime import UTC, datetime
import logging
import requests
from sqlalchemy import and_, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.admin_units import normalize_location
from app.core.job_status import STATUS_DUPLICATE, STATUS_EMPTY, STATUS_FAILED, STATUS_RUNNING, STATUS_SUCCESS
from app.ingestion.records import PriceObservation, ScrapeResult
from app.ingestion.registry import build_scrapers
from app.models import DailyMarketPrice, DurianVariety, ProductionRegion, ScrapeRun


logger = logging.getLogger(__name__)


class PriceIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def scrape_and_store(self, source: str | None = None) -> list[dict]:
        summaries = []
        for scraper in build_scrapers(source):
            started_at = datetime.now(UTC)
            observations: list[PriceObservation] = []
            failed_summary: dict | None = None
            run = ScrapeRun(
                source=scraper.source,
                source_url=scraper.source_url,
                started_at=started_at,
                status=STATUS_RUNNING,
            )
            self.db.add(run)
            self.db.commit()
            try:
                logger.info("Starting scrape: %s", scraper.source)
                result = scraper.scrape()
                inserted, updated = self.store(result)
                observations = result.observations
                run.status = STATUS_SUCCESS
                run.records_found = len(result.observations)
                run.records_inserted = inserted
                run.records_updated = updated
                if len(result.observations) == 0:
                    run.status = STATUS_EMPTY
                    run.error_message = "Parser tìm 0 dữ liệu - kiểm tra HTML nguồn."
                    logger.warning(
                        "Scrape returned 0 records - possibly source HTML changed or no new prices: %s",
                        scraper.source,
                    )
                if inserted == 0 and updated == 0 and len(result.observations) > 0:
                    run.status = STATUS_DUPLICATE
                    run.error_message = "Tất cả dữ liệu trùng với DB - nguồn chưa cập nhật."
                    logger.warning(
                        "Scrape parsed %d records but none persisted (all dedup): %s",
                        len(result.observations),
                        scraper.source,
                    )
                logger.info(
                    "Scrape success: %s found=%d inserted=%d updated=%d",
                    scraper.source,
                    len(result.observations),
                    inserted,
                    updated,
                )
            except requests.Timeout as exc:
                logger.warning("Scrape timeout: %s", scraper.source)
                self.db.rollback()
                run = self.db.get(ScrapeRun, run.id)
                if run:
                    run.status = STATUS_FAILED
                    run.error_message = str(exc)
                failed_summary = {
                    "source": scraper.source,
                    "source_url": scraper.source_url,
                    "status": STATUS_FAILED,
                    "error": str(exc),
                }
            except Exception as exc:
                logger.exception("Scrape failed: %s", scraper.source)
                self.db.rollback()
                run = self.db.get(ScrapeRun, run.id)
                if run:
                    run.status = STATUS_FAILED
                    run.error_message = str(exc)
                failed_summary = {
                    "source": scraper.source,
                    "source_url": scraper.source_url,
                    "status": STATUS_FAILED,
                    "error": str(exc),
                }
            finally:
                if run:
                    run.finished_at = datetime.now(UTC)
                    self.db.add(run)
                    self.db.commit()
                    if failed_summary:
                        summaries.append(failed_summary)
                    else:
                        summaries.append(self._summary(run, observations))
        return summaries

    def store(self, result: ScrapeResult, *, _retry_on_integrity: bool = True) -> tuple[int, int]:
        inserted = 0
        updated = 0
        pending: dict[tuple, DailyMarketPrice] = {}
        for observation in result.observations:
            variety = self._get_or_create_variety(observation.variety_name, observation.crop_type)
            region = self._get_or_create_region(observation.region_name, observation.province)
            key = (
                observation.observed_at,
                variety.variety_id,
                region.region_id,
                observation.quality_grade,
                observation.source,
            )
            if key in pending:
                existing = pending[key]
                existing.crop_type = observation.crop_type
                existing.min_price_vnd = observation.min_price_vnd
                existing.max_price_vnd = observation.max_price_vnd
                existing.volume_traded_tons = observation.volume_traded_tons
                updated += 1
                continue

            existing = self.db.scalar(
                select(DailyMarketPrice).where(
                    and_(
                        DailyMarketPrice.record_timestamp == observation.observed_at,
                        DailyMarketPrice.variety_id == variety.variety_id,
                        DailyMarketPrice.region_id == region.region_id,
                        DailyMarketPrice.quality_grade == observation.quality_grade,
                        DailyMarketPrice.exchange_source == observation.source,
                    )
                )
            )
            if existing:
                existing.crop_type = observation.crop_type
                existing.min_price_vnd = observation.min_price_vnd
                existing.max_price_vnd = observation.max_price_vnd
                existing.volume_traded_tons = observation.volume_traded_tons
                updated += 1
            else:
                price = DailyMarketPrice(
                    record_timestamp=observation.observed_at,
                    crop_type=observation.crop_type,
                    variety_id=variety.variety_id,
                    quality_grade=observation.quality_grade,
                    region_id=region.region_id,
                    exchange_source=observation.source,
                    min_price_vnd=observation.min_price_vnd,
                    max_price_vnd=observation.max_price_vnd,
                    volume_traded_tons=observation.volume_traded_tons,
                )
                self.db.add(price)
                pending[key] = price
                inserted += 1
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if not _retry_on_integrity:
                raise
            logger.info("Price scrape raced an existing insert; retrying store once with fresh DB state.")
            return self.store(result, _retry_on_integrity=False)
        return inserted, updated

    def latest_runs(self, limit: int = 20) -> list[dict]:
        rows = self.db.scalars(select(ScrapeRun).order_by(desc(ScrapeRun.started_at)).limit(limit)).all()
        return [self._run_to_dict(row) for row in rows]

    def _get_or_create_variety(self, name: str, crop_type: str) -> DurianVariety:
        variety = self.db.scalar(select(DurianVariety).where(DurianVariety.name == name))
        if variety:
            variety.crop_type = variety.crop_type or crop_type
            return variety
        variety = DurianVariety(
            name=name,
            crop_type=crop_type,
            description="Được phát hiện từ dữ liệu giá công khai.",
        )
        self.db.add(variety)
        self.db.flush()
        return variety

    def _get_or_create_region(self, region_name: str, province: str | None) -> ProductionRegion:
        region_name, province = normalize_location(region_name, province)
        stmt = select(ProductionRegion).where(
            and_(
                ProductionRegion.region_name == region_name,
                ProductionRegion.province == province,
            )
        )
        region = self.db.scalar(stmt)
        if region:
            return region
        region = ProductionRegion(
            region_name=region_name,
            province=province,
            export_code=None,
            risk_level_index=0.0,
        )
        self.db.add(region)
        self.db.flush()
        return region

    def _summary(self, run: ScrapeRun, observations: list[PriceObservation]) -> dict:
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
