from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import logging
import math
from statistics import median, pstdev
import time

import requests
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.core.cache import invalidate_cache
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult
from app.ingestion.world_fertilizer_registry import build_world_fertilizer_scrapers
from app.models import ScrapeRun, WorldCommodityPrice


logger = logging.getLogger(__name__)
WORLD_FERTILIZER_SCRAPE_ATTEMPTS = 2
WORLD_FERTILIZER_RETRY_DELAY_SECONDS = 2.0
WORLD_FERTILIZER_MODEL_KIND = "world-fertilizer-anchor-ewma-ar1-v2"
MONTHLY_ANCHOR_TREND_CAP = 0.06
DAILY_SIGNAL_DAILY_TREND_CAP = 0.01
DAILY_SIGNAL_SOURCES = {"tradingeconomics_urea_daily"}
DAILY_SIGNAL_MIN_POINTS = 14

COMMODITIES = {
    "urea": {
        "name_vi": "Urê",
        "name_en": "Urea",
        "quote_type": "FOB Middle East",
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
                status="đang chạy",
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
                run.status = "thành công"
                run.records_found = len(observations)
                run.records_inserted = inserted
                run.records_updated = updated
                if len(observations) == 0:
                    run.status = "trống"
                    run.error_message = "Parser tìm 0 dữ liệu commodity phân bón thế giới."
                elif inserted == 0 and updated == 0:
                    run.status = "trùng lặp"
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
                    run.status = "thất bại"
                    run.error_message = str(exc)
                failed_summary = {"source": scraper.source, "source_url": scraper.source_url, "status": "thất bại", "error": str(exc)}
            except Exception as exc:
                logger.exception("World fertilizer scrape failed: %s", scraper.source)
                self.db.rollback()
                run = self.db.get(ScrapeRun, run.id)
                if run:
                    run.status = "thất bại"
                    run.error_message = str(exc)
                failed_summary = {"source": scraper.source, "source_url": scraper.source_url, "status": "thất bại", "error": str(exc)}
            finally:
                if run:
                    run.finished_at = datetime.now(UTC)
                    self.db.add(run)
                    self.db.commit()
                    summaries.append(failed_summary or self._summary(run, observations))
        if summaries:
            invalidate_cache("world-fertilizer")
            invalidate_cache("llm-input-prices")
        return summaries

    def store(self, result: WorldFertilizerScrapeResult) -> tuple[int, int]:
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
        self.db.commit()
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
        checked_source = (
            "world-fertilizer:tradingeconomics_urea_daily"
            if source_mode == "daily_signal"
            else "world-fertilizer:worldbank_pinksheet"
        )
        latest_official_check = self.db.scalar(
            select(ScrapeRun)
            .where(ScrapeRun.source == checked_source)
            .where(ScrapeRun.status.in_(["thành công", "trùng lặp"]))
            .order_by(desc(ScrapeRun.finished_at))
            .limit(1)
        )
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
        base_seasonal = _seasonal_multiplier(base_observed_at)
        forecast_daily: list[dict] = []
        previous_price = base_price
        for day in range(1, horizon + 1):
            forecast_date = today + timedelta(days=day)
            seasonal_ratio = _seasonal_multiplier(datetime(forecast_date.year, forecast_date.month, 1, tzinfo=UTC)) / base_seasonal
            trend_ratio = math.exp(daily_trend * day)
            price = max(base_price * 0.2, base_price * trend_ratio * seasonal_ratio)
            spread = max(0.01, daily_volatility * math.sqrt(day)) * 1.45
            low = max(0, price * (1 - spread))
            high = price * (1 + spread)
            forecast_daily.append(
                {
                    "date": forecast_date.isoformat(),
                    "price_usd_per_tonne": round(price, 2),
                    "price_low_usd_per_tonne": round(low, 2),
                    "price_high_usd_per_tonne": round(high, 2),
                    "daily_pct_change": round(((price / previous_price) - 1) * 100, 3) if previous_price else 0.0,
                    "cumulative_pct_from_today": round(((price / base_price) - 1) * 100, 3),
                }
            )
            previous_price = price

        return {
            "commodity_slug": commodity_slug,
            "commodity_name_vi": meta["name_vi"],
            "quote_type": quote_type,
            "base_price_usd_per_tonne": round(base_price, 2),
            "base_observed_at": base_observed_at,
            "model_kind": WORLD_FERTILIZER_MODEL_KIND,
            "history_points": len(points),
            "volatility": round(daily_volatility, 6),
            "volatility_daily": round(daily_volatility, 6),
            "source_mode": source_mode,
            "data_quality": quality,
            "forecast_daily": forecast_daily,
            "forecast_weekly": _weekly_summary(forecast_daily, base_price),
            "note_vi": _forecast_note(source_mode, base_observed_at),
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
    recent_cutoff = datetime.now(UTC) - timedelta(days=45)
    daily_rows = [row for row in rows if row.source in DAILY_SIGNAL_SOURCES]
    distinct_days = {row.observed_at.date() for row in daily_rows}
    for row in daily_rows:
        observed_at = row.observed_at
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        if observed_at >= recent_cutoff and len(distinct_days) >= DAILY_SIGNAL_MIN_POINTS:
            return "daily_signal"
    return "monthly_official_anchor"


def _model_rows(rows: list[WorldCommodityPrice], source_mode: str) -> list[WorldCommodityPrice]:
    if source_mode == "daily_signal":
        return [row for row in rows if row.source in DAILY_SIGNAL_SOURCES]
    official_rows = [row for row in rows if row.source == "worldbank_pinksheet"]
    return official_rows or rows


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


def _forecast_note(source_mode: str, base_observed_at: datetime) -> str:
    base_date = f"{base_observed_at.day:02d}/{base_observed_at.month:02d}/{base_observed_at.year}"
    common = (
        "Đây là xu hướng giá phân bón thế giới theo USD/tấn, không phải giá bán lẻ nội địa. "
        "Nên dùng tỷ lệ % tăng/giảm làm tín hiệu nền rồi tự áp vào báo giá đại lý, sau khi cộng tỷ giá, vận chuyển và tồn kho."
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
