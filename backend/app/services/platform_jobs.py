from __future__ import annotations

import json
import logging
import os
import errno
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler as APBackgroundScheduler
from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.core.cache import invalidate_cache
from app.core.admin_units import is_crop_province
from app.core.config import get_settings
from app.core.job_status import (
    STATUS_FAILED,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    SUCCESS_STATUSES,
    is_success_status,
    is_terminal_status,
)
from app.db import SessionLocal
from app.ingestion.input_price_service import InputPriceIngestionService
from app.ingestion.service import PriceIngestionService
from app.ml_engine.evaluator import ForecastEvaluator
from app.models import DailyMarketPrice, DurianVariety, ModelTrainingRun, PlatformJobRun, ProductionRegion, RecommendationSession, ScrapeRun, YieldFeedback
from app.services.content_portal import ContentPortalService
from app.services.crop_catalog import CROP_TYPES, ensure_crop_catalog
from app.services.auth import cleanup_expired_revoked_tokens
from app.services.market_intelligence import MarketIntelligenceService
from app.services.ml_model_versions import record_crop_model_version, record_world_fertilizer_model_version
from app.services.model_ready_backfill import ModelReadyBackfillService
from app.services.public_price_calibration import PublicPriceCalibrationService


logger = logging.getLogger(__name__)
SCHEDULER_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
MODEL_READY_HISTORY_DAYS = 240


class PlatformJobService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_scrape(self) -> dict:
        with job_lock("scrape_prices"):
            job = self._start_job("scrape_prices")
            try:
                catalog = ensure_crop_catalog(self.db)
                scrape_results = PriceIngestionService(self.db).scrape_and_store(source=None)
                backfills = [
                    ModelReadyBackfillService(self.db, crop_type=crop, days=MODEL_READY_HISTORY_DAYS).backfill()
                    for crop in CROP_TYPES
                ]
                calibrations = [
                    PublicPriceCalibrationService(self.db, crop_type=crop, days=MODEL_READY_HISTORY_DAYS).calibrate()
                    for crop in CROP_TYPES
                ]
                summary = {
                    "catalog": catalog,
                    "scrape": scrape_results,
                    "backfill": backfills,
                    "public_price_calibration": calibrations,
                }
                invalidate_cache()
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_news_scrape(self) -> dict:
        with job_lock("scrape_news"):
            job = self._start_job("scrape_news")
            try:
                summary = ContentPortalService(self.db).scrape_news()
                invalidate_cache("news")
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_input_price_scrape(self) -> dict:
        with job_lock("scrape_input_prices"):
            job = self._start_job("scrape_input_prices")
            try:
                summary = {"scrape": InputPriceIngestionService(self.db).scrape_and_store(source=None)}
                invalidate_cache("input-price")
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_world_fertilizer_scrape(self, source: str | None = None) -> dict:
        with job_lock("scrape_world_fertilizer"):
            job = self._start_job("scrape_world_fertilizer")
            try:
                from app.services.world_fertilizer import WorldFertilizerIngestionService

                summary = {"scrape": WorldFertilizerIngestionService(self.db).scrape_and_store(source=source)}
                invalidate_cache("world-fertilizer")
                invalidate_cache("llm-input-prices")
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_world_fertilizer_current_scrape(self, *, skip_if_success_today: bool = True) -> dict:
        with job_lock("scrape_world_fertilizer_current"):
            job = self._start_job("scrape_world_fertilizer_current")
            settings = get_settings()
            source = "commoditypriceapi_urea_public_1y"
            try:
                if skip_if_success_today and self._has_successful_scrape_today(f"world-fertilizer:{source}"):
                    summary = {"source": source, "reason": "already_succeeded_today"}
                    self._finish_job(job, STATUS_SKIPPED, summary)
                    return summary

                from app.services.world_fertilizer import WorldFertilizerIngestionService

                attempts = max(1, settings.world_fertilizer_current_retry_attempts)
                delay_seconds = max(1, settings.world_fertilizer_current_retry_delay_seconds)
                scrape_summaries: list[dict] = []
                for attempt in range(1, attempts + 1):
                    result = WorldFertilizerIngestionService(self.db).scrape_and_store(source=source)
                    scrape_summaries.extend(result)
                    if _world_fertilizer_scrape_succeeded(result):
                        summary = {"source": source, "attempts": attempt, "scrape": scrape_summaries}
                        invalidate_cache("world-fertilizer")
                        invalidate_cache("llm-input-prices")
                        self._finish_job(job, STATUS_SUCCESS, summary)
                        return summary
                    if attempt < attempts:
                        time.sleep(delay_seconds)

                summary = {"source": source, "attempts": attempts, "scrape": scrape_summaries}
                message = "CommodityPriceAPI Urea public scrape failed after configured retries."
                self._finish_job(job, STATUS_FAILED, summary, message)
                raise RuntimeError(message)
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                if not is_terminal_status(job.status):
                    self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_weather(self) -> dict:
        with job_lock("weather"):
            job = self._start_job("weather")
            try:
                from app.ingestion.weather import populate_precipitation

                summary = populate_precipitation(self.db, days_back=90)
                invalidate_cache()
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_data_quality(self) -> dict:
        with job_lock("data_quality_check"):
            job = self._start_job("data_quality_check")
            try:
                summary = {
                    "crops": [
                        *(self._quality_summary(crop) for crop in CROP_TYPES),
                    ]
                }
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_retrain(self) -> dict:
        with job_lock("retrain_models"):
            job = self._start_job("retrain_models")
            results = []
            try:
                ensure_crop_catalog(self.db)
                for crop in CROP_TYPES:
                    started = datetime.now(UTC)
                    metrics = ForecastEvaluator(self.db, crop_type=crop).backtest()
                    run = ModelTrainingRun(
                        crop_type=crop,
                        started_at=started,
                        finished_at=datetime.now(UTC),
                        status=STATUS_SUCCESS,
                        rmse_vnd_per_kg=metrics.get("rmse_vnd_per_kg"),
                        mae_vnd_per_kg=metrics.get("mae_vnd_per_kg"),
                        backtest_samples=metrics.get("backtest_samples", 0),
                        evaluated_series=metrics.get("evaluated_series", 0),
                        note=metrics.get("note"),
                    )
                    self.db.add(run)
                    results.append({"crop": crop, **metrics})
                    record_crop_model_version(self.db, crop, metrics=metrics)
                self.db.commit()
                summary = {"models": results}
                invalidate_cache()
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_yield_feedback_reminder(self) -> dict:
        with job_lock("yield_feedback_reminder"):
            job = self._start_job("yield_feedback_reminder")
            try:
                cutoff = datetime.now(UTC) - timedelta(days=21)
                pending = self.db.scalars(
                    select(RecommendationSession)
                    .outerjoin(YieldFeedback, YieldFeedback.session_id == RecommendationSession.session_id)
                    .where(YieldFeedback.feedback_id.is_(None))
                    .where(RecommendationSession.created_at <= cutoff)
                    .order_by(RecommendationSession.created_at.desc())
                    .limit(200)
                ).all()
                summary = {
                    "pending_sessions": len(pending),
                    "sample_session_codes": [item.session_id[:8].upper() for item in pending[:20]],
                    "note": "Email/SMS chưa cấu hình; job giữ danh sách phiên cần nhắc để Tier 2 có dữ liệu năng suất.",
                }
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_revoked_token_cleanup(self) -> dict:
        with job_lock("revoked_token_cleanup"):
            job = self._start_job("revoked_token_cleanup")
            try:
                deleted = cleanup_expired_revoked_tokens(self.db)
                summary = {"deleted": deleted}
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_privacy_cleanup(self) -> dict:
        with job_lock("privacy_cleanup"):
            job = self._start_job("privacy_cleanup")
            try:
                cutoff = datetime.now(UTC) - timedelta(days=7)
                result = self.db.execute(
                    update(RecommendationSession)
                    .where(RecommendationSession.created_at <= cutoff)
                    .where(RecommendationSession.ip_address.is_not(None))
                    .values(ip_address=None)
                )
                self.db.commit()
                summary = {
                    "recommendation_session_ips_cleared": int(result.rowcount or 0),
                    "retention_days": 7,
                }
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def run_model_registry_sync(self) -> dict:
        with job_lock("model_registry_sync"):
            job = self._start_job("model_registry_sync")
            try:
                from app.services.world_fertilizer import COMMODITIES

                registered: list[str] = []
                missing: list[str] = []
                for crop in CROP_TYPES:
                    row = record_crop_model_version(self.db, crop)
                    if row is None:
                        missing.append(f"crop:{crop}")
                    else:
                        registered.append(row.model_key)
                for commodity in COMMODITIES:
                    row = record_world_fertilizer_model_version(self.db, commodity)
                    if row is None:
                        missing.append(f"world-fertilizer:{commodity}")
                    else:
                        registered.append(row.model_key)
                summary = {"registered": registered, "missing": missing}
                self._finish_job(job, STATUS_SUCCESS, summary)
                return summary
            except Exception as exc:
                self.db.rollback()
                job = self.db.get(PlatformJobRun, job.job_id) or job
                self._finish_job(job, STATUS_FAILED, None, str(exc))
                raise

    def latest_jobs(self, limit: int = 20) -> list[PlatformJobRun]:
        return self.db.scalars(select(PlatformJobRun).order_by(desc(PlatformJobRun.started_at)).limit(limit)).all()

    def latest_training_runs(self, limit: int = 10) -> list[ModelTrainingRun]:
        return self.db.scalars(select(ModelTrainingRun).order_by(desc(ModelTrainingRun.started_at)).limit(limit)).all()

    def _has_successful_scrape_today(self, source: str) -> bool:
        local_midnight = datetime.now(SCHEDULER_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        utc_midnight = local_midnight.astimezone(UTC)
        return (
            self.db.scalar(
                select(ScrapeRun)
                .where(
                    ScrapeRun.source == source,
                    ScrapeRun.started_at >= utc_midnight,
                    ScrapeRun.status.in_(SUCCESS_STATUSES),
                    ScrapeRun.records_found > 0,
                )
                .order_by(desc(ScrapeRun.started_at))
                .limit(1)
            )
            is not None
        )

    def _quality_summary(self, crop: str) -> dict:
        service = MarketIntelligenceService(self.db)
        varieties = self.db.scalars(
            select(DurianVariety)
            .where(DurianVariety.crop_type == crop)
            .order_by(DurianVariety.variety_id)
        ).all()
        regions = self.db.scalars(
            select(ProductionRegion)
            .join(DailyMarketPrice, DailyMarketPrice.region_id == ProductionRegion.region_id)
            .where(DailyMarketPrice.crop_type == crop)
            .order_by(ProductionRegion.region_id)
            .distinct()
        ).all()
        production_regions = [
            region
            for region in regions
            if region.province is not None
            and region.region_name not in {"Thị trường Việt Nam", "Chợ đầu mối TP.HCM"}
            and is_crop_province(crop, region.province)
        ]
        scores: list[int] = []
        weak_pairs = []
        stale_pairs = []
        missing_pairs = 0
        quality_by_pair = service.data_quality_bulk(
            crop,
            region_ids=[region.region_id for region in production_regions],
            variety_ids=[variety.variety_id for variety in varieties],
        )
        for region in production_regions:
            for variety in varieties:
                quality = quality_by_pair.get((region.region_id, variety.variety_id))
                if not quality or not quality["history_points"]:
                    missing_pairs += 1
                    continue
                scores.append(quality["score"])
                pair = {
                    "region_id": region.region_id,
                    "province": region.province,
                    "variety_id": variety.variety_id,
                    "variety": variety.name,
                    "score": quality["score"],
                    "history_points": quality["history_points"],
                    "observed_points": quality["observed_points"],
                    "freshness_days": quality["freshness_days"],
                    "risk_flags": quality["risk_flags"],
                }
                if quality["score"] < 80:
                    weak_pairs.append(pair)
                if quality["freshness_days"] is None or quality["freshness_days"] > 3:
                    stale_pairs.append(pair)
        return {
            "crop": crop,
            "pairs_checked": len(production_regions) * len(varieties),
            "missing_pairs": missing_pairs,
            "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "weak_pairs": weak_pairs[:12],
            "stale_pairs": stale_pairs[:12],
        }

    def _start_job(self, name: str) -> PlatformJobRun:
        job = PlatformJobRun(job_name=name, started_at=datetime.now(UTC), status=STATUS_RUNNING)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def _finish_job(
        self,
        job: PlatformJobRun,
        status: str,
        summary: dict | None,
        error_message: str | None = None,
    ) -> None:
        job.finished_at = datetime.now(UTC)
        job.status = status
        job.summary = json.dumps(summary, ensure_ascii=False, default=str) if summary is not None else None
        job.error_message = error_message
        self.db.add(job)
        self.db.commit()


def _world_fertilizer_scrape_succeeded(results: list[dict]) -> bool:
    for item in results:
        status = str(item.get("status") or "").strip().lower()
        if is_success_status(status) and int(item.get("records_found") or 0) > 0:
            return True
    return False


class JobScheduler:
    _scheduler: APBackgroundScheduler | None = None

    @classmethod
    def start_once(cls) -> None:
        if cls._scheduler is not None:
            return
        settings = get_settings()
        cls._scheduler = APBackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=2)},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 24 * 60 * 60,
            },
            timezone=SCHEDULER_TZ,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour="6-22",
            minute=0,
            args=["scrape"],
            id="scrape_prices_business_hours",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "date",
            run_date=datetime.now(SCHEDULER_TZ) + timedelta(seconds=10),
            args=["scrape"],
            id="scrape_prices_boot_catchup",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour="6,10,14,18",
            minute=30,
            args=["input_prices"],
            id="scrape_input_prices_quarter_day",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "date",
            run_date=datetime.now(SCHEDULER_TZ) + timedelta(seconds=15),
            args=["input_prices"],
            id="scrape_input_prices_boot_catchup",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour=8,
            minute=30,
            args=["world_fertilizer_official"],
            id="scrape_worldbank_daily",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "date",
            run_date=datetime.now(SCHEDULER_TZ) + timedelta(seconds=25),
            args=["world_fertilizer_official"],
            id="scrape_worldbank_boot_catchup",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour=9,
            minute=0,
            args=["world_fertilizer_current"],
            id="scrape_commoditypriceapi_urea_daily_0900",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour="9-23",
            minute="15,30,45",
            args=["world_fertilizer_current_retry"],
            id="scrape_commoditypriceapi_urea_retry_until_success",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "interval",
            minutes=settings.news_scrape_interval_minutes,
            args=["news"],
            id="scrape_news_every_3h",
            next_run_time=datetime.now(SCHEDULER_TZ) + timedelta(seconds=20),
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour=settings.news_scrape_daily_hour,
            minute=settings.news_scrape_daily_minute,
            args=["news"],
            id="scrape_news_daily_0700",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "interval",
            minutes=settings.data_quality_interval_minutes,
            args=["data_quality"],
            id="data_quality",
            next_run_time=datetime.now(SCHEDULER_TZ) + timedelta(minutes=settings.data_quality_interval_minutes),
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour=4,
            minute=0,
            args=["weather"],
            id="weather_daily_0400",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "interval",
            minutes=settings.retrain_interval_minutes,
            args=["retrain"],
            id="retrain",
            next_run_time=datetime.now(SCHEDULER_TZ) + timedelta(minutes=settings.retrain_interval_minutes),
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            day=1,
            hour=7,
            minute=30,
            args=["yield_feedback_reminder"],
            id="yield_feedback_reminder_monthly",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour=3,
            minute=20,
            args=["revoked_token_cleanup"],
            id="revoked_token_cleanup_daily",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour=3,
            minute=35,
            args=["privacy_cleanup"],
            id="privacy_cleanup_daily",
            replace_existing=True,
        )
        cls._scheduler.add_job(
            cls._run_with_session,
            "cron",
            hour=3,
            minute=45,
            args=["model_registry_sync"],
            id="model_registry_sync_daily",
            replace_existing=True,
        )
        cls._scheduler.start()

    @classmethod
    def shutdown(cls) -> None:
        if cls._scheduler is not None:
            cls._scheduler.shutdown(wait=True)
            cls._scheduler = None

    @staticmethod
    def _run_with_session(job: str) -> None:
        with SessionLocal() as db:
            service = PlatformJobService(db)
            try:
                if job == "scrape":
                    service.run_scrape()
                elif job == "input_prices":
                    service.run_input_price_scrape()
                elif job == "world_fertilizer":
                    service.run_world_fertilizer_scrape()
                elif job == "world_fertilizer_official":
                    service.run_world_fertilizer_scrape(source="worldbank_pinksheet")
                elif job in {"world_fertilizer_current", "world_fertilizer_current_retry"}:
                    service.run_world_fertilizer_current_scrape(skip_if_success_today=True)
                elif job == "news":
                    service.run_news_scrape()
                elif job == "data_quality":
                    service.run_data_quality()
                elif job == "retrain":
                    service.run_retrain()
                elif job == "weather":
                    service.run_weather()
                elif job == "yield_feedback_reminder":
                    service.run_yield_feedback_reminder()
                elif job == "revoked_token_cleanup":
                    service.run_revoked_token_cleanup()
                elif job == "privacy_cleanup":
                    service.run_privacy_cleanup()
                elif job == "model_registry_sync":
                    service.run_model_registry_sync()
            except Exception:
                logger.exception("Scheduled job %s failed", job)

@contextmanager
def job_lock(name: str):
    lock_dir = Path(os.getenv("MARKETAI_JOB_LOCK_DIR", Path.cwd() / ".job_locks"))
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{name}.lock"
    handle = None
    acquired = False
    try:
        try:
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            if not _is_stale_lock(lock_path):
                raise RuntimeError(f"Job {name} đang chạy, bỏ qua lần chạy chồng.") from exc
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
            handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            logger.warning("Reset stale job lock: %s", name)
        acquired = True
        os.write(handle, json.dumps({"pid": os.getpid(), "at": time.time()}).encode("utf-8"))
        yield
    finally:
        if handle is not None:
            os.close(handle)
        if acquired:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass


def _is_stale_lock(lock_path: Path, max_age_seconds: int = 6 * 3600) -> bool:
    try:
        raw = lock_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return True
    try:
        meta = json.loads(raw)
        pid = int(meta.get("pid", 0))
        created_at = float(meta.get("at", 0))
    except (TypeError, ValueError, json.JSONDecodeError):
        try:
            pid = int(raw.strip())
            created_at = lock_path.stat().st_mtime
        except (ValueError, OSError):
            return True

    if pid <= 0 or time.time() - created_at > max_age_seconds:
        return True
    try:
        os.kill(pid, 0)
        return False
    except OSError as exc:
        return exc.errno == errno.ESRCH

