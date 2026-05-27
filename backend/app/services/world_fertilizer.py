from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import logging
import math
from statistics import median, pstdev
import time

import requests
from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import invalidate_cache
from app.core.job_status import (
    STATUS_DUPLICATE,
    STATUS_EMPTY,
    STATUS_FAILED,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    SUCCESS_STATUSES,
)
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult
from app.ingestion.world_fertilizer_registry import build_world_fertilizer_scrapers
from app.ml_engine.world_fertilizer_lstm import predict_world_fertilizer_lstm
from app.models import ScrapeRun, WorldCommodityPrice
from app.services.ops_alerts import send_ops_alert


logger = logging.getLogger(__name__)
WORLD_FERTILIZER_SCRAPE_ATTEMPTS = 2
WORLD_FERTILIZER_RETRY_DELAY_SECONDS = 2.0
WORLD_FERTILIZER_MODEL_KIND = "world-fertilizer-anchor-ewma-ar1-v2"
MONTHLY_ANCHOR_TREND_CAP = 0.06
DAILY_SIGNAL_DAILY_TREND_CAP = 0.01
PRIMARY_DAILY_SIGNAL_SOURCES = {"commoditypriceapi_urea_public_1y"}
DAILY_SIGNAL_SOURCES = {
    *PRIMARY_DAILY_SIGNAL_SOURCES,
    "tradingeconomics_urea_daily",
    "yahoo_urea_futures_daily",
    "investing_urea_current",
}
DAILY_SIGNAL_MIN_POINTS = 14
DAILY_SIGNAL_STALE_AFTER_DAYS = 45
MONTHLY_ANCHOR_STALE_AFTER_DAYS = 90

COMMODITIES = {
    "urea": {
        "name_vi": "Urê",
        "name_en": "Urea",
        "quote_type": "Benchmark USD/tan",
        "driver_note_vi": "Urê thường nhạy với khí gas, than và nguồn cung Trung Quốc/Trung Đông.",
    },
    "dap": {
        "name_vi": "DAP",
        "name_en": "Diammonium phosphate",
        "quote_type": "FOB US Gulf",
        "driver_note_vi": "DAP chịu ảnh hưởng bởi phosphate rock, lưu huỳnh và chi phí logistics.",
    },
    "kali_mop": {
        "name_vi": "Kali (MOP)",
        "name_en": "Potassium chloride",
        "quote_type": "Brazil CFR / FOB Vancouver",
        "driver_note_vi": "Kali Việt Nam phụ thuộc nhiều vào nhập khẩu, nên xu hướng thế giới là tín hiệu nền quan trọng.",
    },
}


class WorldFertilizerIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def scrape_and_store(self, source: str | None = None) -> list[dict]:
        summaries = []
        for scraper in build_world_fertilizer_scrapers(source):
            started_at = datetime.now(UTC)
            observations: list[WorldFertilizerObservation] = []
            failed_summary: dict | None = None
            run = ScrapeRun(
                source=f"world-fertilizer:{scraper.source}",
                source_url=scraper.source_url,
                started_at=started_at,
                status=STATUS_RUNNING,
            )
            self.db.add(run)
            self.db.commit()
            try:
                result = None
                last_error: Exception | None = None
                for attempt in range(1, WORLD_FERTILIZER_SCRAPE_ATTEMPTS + 1):
                    logger.info("Starting world fertilizer scrape: %s attempt=%d", scraper.source, attempt)
                    try:
                        candidate = scraper.scrape()
                    except Exception as exc:
                        last_error = exc
                        if attempt < WORLD_FERTILIZER_SCRAPE_ATTEMPTS:
                            logger.warning(
                                "World fertilizer scrape attempt failed, retrying: %s attempt=%d error=%s",
                                scraper.source,
                                attempt,
                                exc,
                            )
                            time.sleep(WORLD_FERTILIZER_RETRY_DELAY_SECONDS)
                            continue
                        raise
                    if candidate.observations or attempt >= WORLD_FERTILIZER_SCRAPE_ATTEMPTS:
                        result = candidate
                        break
                    logger.warning("World fertilizer scrape returned 0 records, retrying: %s attempt=%d", scraper.source, attempt)
                    time.sleep(WORLD_FERTILIZER_RETRY_DELAY_SECONDS)
                if result is None:
                    raise last_error or RuntimeError(f"World fertilizer scrape did not return a result: {scraper.source}")
                inserted, updated = self.store(result)
                observations = result.observations
                run.source_url = result.source_url
                run.status = STATUS_SUCCESS
                run.records_found = len(observations)
                run.records_inserted = inserted
                run.records_updated = updated
                if len(observations) == 0:
                    run.status = STATUS_EMPTY
                    run.error_message = "Parser tìm 0 dữ liệu commodity phân bón thế giới."
                elif inserted == 0 and updated == 0:
                    run.status = STATUS_DUPLICATE
                    run.error_message = "Tất cả dữ liệu commodity phân bón thế giới trùng với DB."
                logger.info(
                    "World fertilizer scrape success: %s found=%d inserted=%d updated=%d",
                    scraper.source,
                    len(observations),
                    inserted,
                    updated,
                )
            except requests.Timeout as exc:
                self.db.rollback()
                run = self.db.get(ScrapeRun, run.id)
                if run:
                    run.status = STATUS_FAILED
                    run.error_message = str(exc)
                failed_summary = {"source": scraper.source, "source_url": scraper.source_url, "status": STATUS_FAILED, "error": str(exc)}
            except Exception as exc:
                logger.exception("World fertilizer scrape failed: %s", scraper.source)
                self.db.rollback()
                run = self.db.get(ScrapeRun, run.id)
                if run:
                    run.status = STATUS_FAILED
                    run.error_message = str(exc)
                failed_summary = {"source": scraper.source, "source_url": scraper.source_url, "status": STATUS_FAILED, "error": str(exc)}
            finally:
                if run:
                    run.finished_at = datetime.now(UTC)
                    self.db.add(run)
                    self.db.commit()
                    summary = failed_summary or self._summary(run, observations)
                    summaries.append(summary)
                    if failed_summary:
                        send_ops_alert(
                            "world_fertilizer_scrape_failed",
                            {
                                "run_id": run.id,
                                "source": scraper.source,
                                "source_url": scraper.source_url,
                                "status": run.status,
                                "error_message": run.error_message,
                                "started_at": run.started_at.isoformat() if run.started_at else None,
                                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                            },
                        )
        if summaries:
            invalidate_cache("world-fertilizer")
            invalidate_cache("llm-input-prices")
        return summaries

    def store(self, result: WorldFertilizerScrapeResult, *, _retry_on_integrity: bool = True) -> tuple[int, int]:
        inserted = 0
        updated = 0
        pending: dict[tuple[str, str, str, datetime], WorldCommodityPrice] = {}
        for observation in result.observations:
            if observation.commodity_slug not in COMMODITIES:
                continue
            key = (
                observation.commodity_slug,
                observation.source,
                observation.quote_type,
                observation.observed_at,
            )
            if key in pending:
                _apply_observation(pending[key], observation)
                updated += 1
                continue
            existing = self.db.scalar(
                select(WorldCommodityPrice).where(
                    and_(
                        WorldCommodityPrice.commodity_slug == observation.commodity_slug,
                        WorldCommodityPrice.source == observation.source,
                        WorldCommodityPrice.quote_type == observation.quote_type,
                        WorldCommodityPrice.observed_at == observation.observed_at,
                    )
                )
            )
            if existing:
                _apply_observation(existing, observation)
                updated += 1
                continue
            row = WorldCommodityPrice(
                commodity_slug=observation.commodity_slug,
                quote_type=observation.quote_type,
                source=observation.source,
                source_url=observation.source_url,
                observed_at=observation.observed_at,
                price_usd_per_tonne=observation.price_usd_per_tonne,
                currency="USD",
                confidence_score=observation.confidence_score,
                raw_json=observation.raw_json,
                created_at=datetime.now(UTC),
            )
            self.db.add(row)
            pending[key] = row
            inserted += 1
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            if not _retry_on_integrity:
                raise
            logger.info("World fertilizer scrape raced an existing insert; retrying store once with fresh DB state.")
            return self.store(result, _retry_on_integrity=False)
        return inserted, updated

    def _summary(self, run: ScrapeRun, observations: list[WorldFertilizerObservation]) -> dict:
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
            "sample": [asdict(item) for item in observations[:5]],
        }


class WorldFertilizerForecastService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def commodities(self) -> list[dict]:
        return [
            {
                "commodity_slug": slug,
                "name_vi": meta["name_vi"],
                "name_en": meta["name_en"],
                "quote_type": meta["quote_type"],
                "driver_note_vi": meta["driver_note_vi"],
            }
            for slug, meta in COMMODITIES.items()
        ]

    def history(self, commodity_slug: str, days: int = 365) -> list[dict]:
        self._validate_commodity(commodity_slug)
        since = datetime.now(UTC) - timedelta(days=max(days, 1))
        rows = self.db.scalars(
            select(WorldCommodityPrice)
            .where(WorldCommodityPrice.commodity_slug == commodity_slug, WorldCommodityPrice.observed_at >= since)
            .order_by(WorldCommodityPrice.observed_at)
            .limit(2000)
        ).all()
        source_mode = _source_mode(rows)
        return [self._history_row(row) for row in _model_rows(rows, source_mode)]

    def forecast(self, commodity_slug: str, horizon_days: int = 30) -> dict:
        self._validate_commodity(commodity_slug)
        horizon = min(max(horizon_days, 1), 60)
        rows = list(
            reversed(
                self.db.scalars(
                    select(WorldCommodityPrice)
                    .where(WorldCommodityPrice.commodity_slug == commodity_slug)
                    .order_by(desc(WorldCommodityPrice.observed_at))
                    .limit(3000)
                ).all()
            )
        )
        source_mode = _source_mode(rows)
        selected_rows = _model_rows(rows, source_mode)
        points = _aggregate_observations(selected_rows)
        meta = COMMODITIES[commodity_slug]
        if len(points) < 14:
            return {
                "commodity_slug": commodity_slug,
                "commodity_name_vi": meta["name_vi"],
                "quote_type": meta["quote_type"],
                "base_price_usd_per_tonne": None,
                "base_observed_at": None,
                "model_kind": "insufficient-data",
                "history_points": len(points),
                "volatility": 0.0,
                "volatility_daily": 0.0,
                "source_mode": "insufficient-data",
                "data_quality": {
                    "level": "low",
                    "reason_vi": "Chưa đủ tối thiểu 14 điểm lịch sử để nội suy xu hướng 30 ngày.",
                    "latest_source": None,
                    "latest_observed_at": None,
                },
                "forecast_daily": [],
                "forecast_weekly": [],
                "note_vi": "Chưa đủ dữ liệu lịch sử để dự báo xu hướng phân bón thế giới.",
            }

        base_observed_at, base_price, quote_type = points[-1]
        quality = _data_quality(selected_rows, points, source_mode)
        checked_sources = (
            [f"world-fertilizer:{source}" for source in DAILY_SIGNAL_SOURCES]
            if source_mode == "daily_signal"
            else ["world-fertilizer:worldbank_pinksheet"]
        )
        latest_official_check = _latest_successful_scrape_run(self.db, checked_sources)
        quality["last_source_check_at"] = (
            latest_official_check.finished_at.isoformat()
            if latest_official_check and latest_official_check.finished_at
            else None
        )
        returns = [
            math.log(points[index][1] / points[index - 1][1])
            for index in range(1, len(points))
            if points[index - 1][1] > 0 and points[index][1] > 0
        ][-36:]
        raw_trend = _monthly_trend(returns)
        raw_volatility = pstdev(returns) if len(returns) > 1 else 0.0
        if source_mode == "daily_signal":
            daily_trend = max(min(raw_trend, DAILY_SIGNAL_DAILY_TREND_CAP), -DAILY_SIGNAL_DAILY_TREND_CAP)
            daily_volatility = min(max(raw_volatility, 0.0012), 0.018)
        else:
            monthly_trend = max(min(raw_trend, MONTHLY_ANCHOR_TREND_CAP), -MONTHLY_ANCHOR_TREND_CAP)
            daily_trend = monthly_trend / 30
            daily_volatility = min(max(raw_volatility / math.sqrt(30), 0.0012), 0.012)
        today = datetime.now(UTC).date()
        staleness_days = _staleness_days(base_observed_at)
        stale_after_days = DAILY_SIGNAL_STALE_AFTER_DAYS if source_mode == "daily_signal" else MONTHLY_ANCHOR_STALE_AFTER_DAYS
        is_stale = staleness_days > stale_after_days
        quality["staleness_days"] = staleness_days
        quality["stale_after_days"] = stale_after_days
        quality["is_stale"] = is_stale
        if is_stale:
            logger.warning(
                "World fertilizer forecast anchor is stale commodity=%s source_mode=%s observed_at=%s staleness_days=%s",
                commodity_slug,
                source_mode,
                base_observed_at,
                staleness_days,
            )

        lstm_prediction = (
            predict_world_fertilizer_lstm(commodity_slug, points, horizon_days=horizon)
            if source_mode == "daily_signal" and not is_stale
            else None
        )
        if lstm_prediction is not None:
            forecast_daily = _forecast_daily_from_prices(
                predicted_prices=lstm_prediction.prices,
                base_price=base_price,
                today=today,
                daily_volatility=daily_volatility,
            )
            model_kind = lstm_prediction.model_kind
            quality["model_artifact"] = {
                "model_kind": lstm_prediction.model_kind,
                "source": lstm_prediction.meta.get("source"),
                "last_observed_at": lstm_prediction.meta.get("last_observed_at"),
                "validation_mae_usd_per_tonne": lstm_prediction.meta.get("validation_mae_usd_per_tonne"),
                "validation_rmse_improvement_pct": lstm_prediction.meta.get("validation_rmse_improvement_pct"),
            }
        else:
            base_seasonal = _seasonal_multiplier(base_observed_at)
            predicted_prices = []
            for day in range(1, horizon + 1):
                forecast_date = today + timedelta(days=day)
                seasonal_ratio = _seasonal_multiplier(datetime(forecast_date.year, forecast_date.month, 1, tzinfo=UTC)) / base_seasonal
                trend_ratio = math.exp(daily_trend * day)
                predicted_prices.append(max(base_price * 0.2, base_price * trend_ratio * seasonal_ratio))
            forecast_daily = _forecast_daily_from_prices(
                predicted_prices=predicted_prices,
                base_price=base_price,
                today=today,
                daily_volatility=daily_volatility,
            )
            model_kind = WORLD_FERTILIZER_MODEL_KIND

        return {
            "commodity_slug": commodity_slug,
            "commodity_name_vi": meta["name_vi"],
            "quote_type": quote_type,
            "base_price_usd_per_tonne": round(base_price, 2),
            "base_observed_at": base_observed_at,
            "model_kind": model_kind,
            "history_points": len(points),
            "volatility": round(daily_volatility, 6),
            "volatility_daily": round(daily_volatility, 6),
            "source_mode": source_mode,
            "data_quality": quality,
            "forecast_daily": forecast_daily,
            "forecast_weekly": _weekly_summary(forecast_daily, base_price),
            "note_vi": _forecast_note(source_mode, base_observed_at, model_kind),
        }

    def health(self, stale_after_days: int = 45) -> dict:
        latest_by_commodity = {}
        for slug in COMMODITIES:
            latest = self.db.scalar(
                select(func.max(WorldCommodityPrice.observed_at)).where(WorldCommodityPrice.commodity_slug == slug)
            )
            latest_by_commodity[slug] = latest
        latest_run = self.db.scalar(
            select(ScrapeRun)
            .where(ScrapeRun.source.like("world-fertilizer:%"))
            .order_by(desc(ScrapeRun.started_at))
            .limit(1)
        )
        now = datetime.now(UTC)
        stale = []
        for slug, observed_at in latest_by_commodity.items():
            if observed_at is None:
                stale.append(slug)
                continue
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=UTC)
            if (now - observed_at).days > stale_after_days:
                stale.append(slug)
        return {
            "category": "world-fertilizer",
            "commodities": latest_by_commodity,
            "status": "stale" if stale else "ok",
            "stale_commodities": stale,
            "latest_run": {
                "source": latest_run.source,
                "status": latest_run.status,
                "finished_at": latest_run.finished_at,
                "error_message": latest_run.error_message,
            }
            if latest_run
            else None,
        }

    @staticmethod
    def _history_row(row: WorldCommodityPrice) -> dict:
        return {
            "observed_at": row.observed_at,
            "price_usd_per_tonne": float(row.price_usd_per_tonne),
            "quote_type": row.quote_type,
            "source": row.source,
            "source_url": row.source_url,
            "confidence_score": float(row.confidence_score),
        }

    @staticmethod
    def _validate_commodity(commodity_slug: str) -> None:
        if commodity_slug not in COMMODITIES:
            raise ValueError("Mã phân bón thế giới không hợp lệ.")


def _apply_observation(row: WorldCommodityPrice, observation: WorldFertilizerObservation) -> None:
    row.source_url = observation.source_url
    row.price_usd_per_tonne = observation.price_usd_per_tonne
    row.currency = "USD"
    row.confidence_score = observation.confidence_score
    row.raw_json = observation.raw_json


def _aggregate_observations(rows: list[WorldCommodityPrice]) -> list[tuple[datetime, float, str]]:
    grouped: dict[datetime, list[WorldCommodityPrice]] = {}
    for row in rows:
        day = row.observed_at.replace(hour=0, minute=0, second=0, microsecond=0)
        grouped.setdefault(day, []).append(row)
    points: list[tuple[datetime, float, str]] = []
    for observed_at, items in grouped.items():
        values = [float(item.price_usd_per_tonne) for item in items if item.price_usd_per_tonne is not None]
        if not values:
            continue
        strongest = max(items, key=lambda item: float(item.confidence_score))
        points.append((observed_at, median(values), strongest.quote_type))
    return sorted(points, key=lambda item: item[0])


def _source_mode(rows: list[WorldCommodityPrice]) -> str:
    primary_daily_rows = [row for row in rows if row.source in PRIMARY_DAILY_SIGNAL_SOURCES]
    if _has_recent_daily_signal(primary_daily_rows):
        return "daily_signal"
    daily_rows = [row for row in rows if row.source in DAILY_SIGNAL_SOURCES]
    if _has_recent_daily_signal(daily_rows):
        return "daily_signal"
    return "monthly_official_anchor"


def _model_rows(rows: list[WorldCommodityPrice], source_mode: str) -> list[WorldCommodityPrice]:
    if source_mode == "daily_signal":
        primary_rows = [row for row in rows if row.source in PRIMARY_DAILY_SIGNAL_SOURCES]
        if _has_recent_daily_signal(primary_rows):
            return _select_consistent_quote_rows(primary_rows)
        return _select_consistent_quote_rows([row for row in rows if row.source in DAILY_SIGNAL_SOURCES])
    official_rows = [row for row in rows if row.source == "worldbank_pinksheet"]
    return official_rows or rows


def _select_consistent_quote_rows(rows: list[WorldCommodityPrice]) -> list[WorldCommodityPrice]:
    if not rows:
        return []
    by_quote_type: dict[str, list[WorldCommodityPrice]] = {}
    for row in rows:
        by_quote_type.setdefault(row.quote_type, []).append(row)
    if len(by_quote_type) == 1:
        return rows

    def score(items: list[WorldCommodityPrice]) -> tuple[int, datetime, int, float]:
        latest = max(_aware_utc(row.observed_at) for row in items)
        distinct_days = len({row.observed_at.date() for row in items})
        avg_confidence = sum(float(row.confidence_score or 0) for row in items) / max(1, len(items))
        recent_signal = 1 if _has_recent_daily_signal(items) else 0
        return (recent_signal, latest, distinct_days, avg_confidence)

    selected_quote_type, selected_rows = max(by_quote_type.items(), key=lambda item: score(item[1]))
    logger.info(
        "Selected world fertilizer quote_type=%s among %d quote types for model consistency",
        selected_quote_type,
        len(by_quote_type),
    )
    return selected_rows


def _has_recent_daily_signal(rows: list[WorldCommodityPrice]) -> bool:
    recent_cutoff = datetime.now(UTC) - timedelta(days=45)
    recent_days = {row.observed_at.date() for row in rows if _aware_utc(row.observed_at) >= recent_cutoff}
    return len(recent_days) >= DAILY_SIGNAL_MIN_POINTS


def _aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _staleness_days(value: datetime) -> int:
    return max(0, (datetime.now(UTC) - _aware_utc(value)).days)


def _data_quality(rows: list[WorldCommodityPrice], points: list[tuple[datetime, float, str]], source_mode: str) -> dict:
    latest_row = max(rows, key=lambda row: row.observed_at)
    latest_observed_at = latest_row.observed_at
    if latest_observed_at.tzinfo is None:
        latest_observed_at = latest_observed_at.replace(tzinfo=UTC)
    staleness_days = max(0, (datetime.now(UTC) - latest_observed_at).days)
    if source_mode == "daily_signal":
        level = "high" if staleness_days <= 7 else "medium"
        reason = "Có tín hiệu nguồn tin daily gần đây, World Bank Pink Sheet dùng làm neo kiểm chứng."
    else:
        level = "medium" if staleness_days <= 75 else "low"
        reason = (
            "Nguồn chính hiện là World Bank Pink Sheet theo tháng. Bảng ngày phía dưới là nội suy xu hướng 30 ngày "
            "từ dữ liệu chính thức, không phải báo giá daily ngoài thị trường."
        )
    sources = sorted({row.source for row in rows})
    return {
        "level": level,
        "source_mode": source_mode,
        "sources": sources,
        "history_points": len(points),
        "latest_source": latest_row.source,
        "latest_observed_at": latest_observed_at.isoformat(),
        "staleness_days": staleness_days,
        "reason_vi": reason,
    }


def _latest_successful_scrape_run(db: Session, sources: list[str]) -> ScrapeRun | None:
    if not sources:
        return None
    return db.scalar(
        select(ScrapeRun)
        .where(ScrapeRun.source.in_(sources), ScrapeRun.status.in_(SUCCESS_STATUSES))
        .order_by(desc(ScrapeRun.finished_at), desc(ScrapeRun.started_at))
        .limit(1)
    )


def _forecast_daily_from_prices(
    *,
    predicted_prices: list[float],
    base_price: float,
    today,
    daily_volatility: float,
) -> list[dict]:
    forecast_daily: list[dict] = []
    previous_price = base_price
    band_width = min(max(daily_volatility * 1.35, 0.004), 0.035)
    for index, raw_price in enumerate(predicted_prices, start=1):
        price = max(base_price * 0.2, float(raw_price))
        forecast_date = today + timedelta(days=index)
        pct_change_vs_today = ((price / base_price) - 1) * 100 if base_price else 0.0
        pct_change_vs_prev_day = ((price / previous_price) - 1) * 100 if previous_price else 0.0
        forecast_daily.append(
            {
                "day_index": index,
                "date": forecast_date.isoformat(),
                "price_usd_per_tonne": round(price, 2),
                "price_low_usd_per_tonne": round(price * (1 - band_width), 2),
                "price_high_usd_per_tonne": round(price * (1 + band_width), 2),
                "daily_pct_change": round(pct_change_vs_prev_day, 3),
                "cumulative_pct_from_today": round(pct_change_vs_today, 3),
                "pct_change_vs_today": round(pct_change_vs_today, 3),
                "pct_change_vs_prev_day": round(pct_change_vs_prev_day, 3),
            }
        )
        previous_price = price
    return forecast_daily


def _forecast_note(source_mode: str, base_observed_at: datetime, model_kind: str) -> str:
    base_date = f"{base_observed_at.day:02d}/{base_observed_at.month:02d}/{base_observed_at.year}"
    common = (
        "Đây là xu hướng giá phân bón thế giới theo USD/tấn, không phải giá bán lẻ nội địa. "
        "Nên dùng tỷ lệ % tăng/giảm làm tín hiệu nền rồi tự áp vào báo giá đại lý, sau khi cộng tỷ giá, vận chuyển và tồn kho."
    )
    if model_kind.startswith("world-fertilizer-lstm"):
        return (
            f"Mô hình LSTM đang dùng chuỗi daily benchmark mới nhất đến ngày {base_date} để dự báo 30 ngày. "
            f"{common}"
        )
    if source_mode == "monthly_official_anchor":
        return (
            f"Dữ liệu chính thức mới nhất đang neo ở World Bank Pink Sheet ngày {base_date}. "
            "Daily breakdown là nội suy thận trọng từ xu hướng monthly, đã cap biên độ để tránh phóng đại. "
            f"{common}"
        )
    return f"Có tín hiệu nguồn daily gần đây và World Bank dùng làm neo kiểm chứng. {common}"


def _monthly_trend(returns: list[float]) -> float:
    if not returns:
        return 0.0
    ewma = returns[0]
    alpha = 0.35
    for value in returns[1:]:
        ewma = alpha * value + (1 - alpha) * ewma
    average = sum(returns) / len(returns)
    if len(returns) < 3:
        return max(min(ewma, 0.18), -0.18)
    variance = sum((value - average) ** 2 for value in returns[:-1])
    if variance <= 0:
        ar_component = returns[-1]
    else:
        covariance = sum((returns[index] - average) * (returns[index + 1] - average) for index in range(len(returns) - 1))
        phi = max(min(covariance / variance, 0.8), -0.5)
        ar_component = average + phi * (returns[-1] - average)
    trend = 0.65 * ewma + 0.35 * ar_component
    return max(min(trend, 0.22), -0.22)


def _seasonal_multiplier(ts: datetime) -> float:
    multipliers = {
        1: 1.010,
        2: 1.012,
        3: 1.008,
        4: 1.000,
        5: 0.996,
        6: 0.994,
        7: 0.998,
        8: 1.002,
        9: 1.006,
        10: 1.010,
        11: 1.012,
        12: 1.006,
    }
    return multipliers.get(ts.month, 1.0)


def _weekly_summary(forecast_daily: list[dict], base_price: float) -> list[dict]:
    weeks: list[dict] = []
    previous_median = base_price
    for index in range(0, len(forecast_daily), 7):
        items = forecast_daily[index : index + 7]
        if not items:
            continue
        week_index = len(weeks) + 1
        prices = [item["price_usd_per_tonne"] for item in items]
        week_median = median(prices)
        date_from = items[0]["date"]
        date_to = items[-1]["date"]
        weeks.append(
            {
                "week_index": week_index,
                "week_label_vi": f"Tuần {week_index}: {_short_date(date_from)} - {_short_date(date_to)}",
                "date_from": date_from,
                "date_to": date_to,
                "median_price_usd_per_tonne": round(week_median, 2),
                "low_price_usd_per_tonne": round(min(item["price_low_usd_per_tonne"] for item in items), 2),
                "high_price_usd_per_tonne": round(max(item["price_high_usd_per_tonne"] for item in items), 2),
                "pct_change_vs_prev_week": round(((week_median / previous_median) - 1) * 100, 3) if previous_median else 0.0,
                "pct_change_vs_today": round(((week_median / base_price) - 1) * 100, 3) if base_price else 0.0,
                "daily_breakdown": items,
            }
        )
        previous_median = week_median
    return weeks


def _short_date(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return f"{parsed.day:02d}/{parsed.month:02d}"
