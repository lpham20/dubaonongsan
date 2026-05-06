from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.core.admin_units import is_production_region
from app.core.cache import cached
from app.core.config import get_settings
from app.db import get_db
from app.ml_engine.lstm_forecaster import ForecastConfig, LSTMForecaster
from app.ml_engine.signal_processor import detect_optimal_sell_points
from app.models import DailyMarketPrice, DurianVariety, ModelTrainingRun, ProductionRegion, UserPriceReport
from app.schemas import ForecastPoint, HistoricalPricePoint, ModelMetrics, TradingSignal
from app.services.data_loader import DataLoader
from app.services.exports import rows_to_pdf, rows_to_xlsx
from app.services.market_intelligence import MarketIntelligenceService


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["analytics"])


@router.get("/analytics/ticker-prices", response_model=list[HistoricalPricePoint])
@cached(prefix="ticker", ttl_seconds=300)
def ticker_prices(
    crop: str = Query(default="sau_rieng"),
    limit: int = Query(default=40, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = DataLoader(db).historical_prices(crop_type=crop, quality_grade=None, limit=1000)
    latest_by_key: dict[tuple[str, str | None, str | None, str | None], dict] = {}
    for row in rows:
        if not is_production_region(row.get("region"), row.get("province")):
            continue
        key = (row["variety"], row["region"], row["province"], row["quality_grade"])
        latest_by_key[key] = row
    return sorted(latest_by_key.values(), key=lambda item: item["timestamp"], reverse=True)[:limit]


@router.get("/analytics/daily-price-board", response_model=list[HistoricalPricePoint])
@cached(prefix="daily-price-board", ttl_seconds=300)
def daily_price_board(
    crop: str = Query(default="sau_rieng"),
    limit: int = Query(default=500, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = DataLoader(db).historical_prices(crop_type=crop, quality_grade=None, limit=10000)
    latest_by_key: dict[tuple[str, str | None, str | None, str | None], dict] = {}
    for row in rows:
        if not is_production_region(row.get("region"), row.get("province")):
            continue
        source = row.get("exchange_source") or ""
        if source in {"model-ready-backfill", "Người dùng báo giá"}:
            continue
        key = (row["variety"], row["region"], row["province"], row["quality_grade"])
        latest_by_key[key] = row

    board = sorted(
        latest_by_key.values(),
        key=lambda item: (
            item.get("province") or "",
            item.get("region") or "",
            item.get("variety") or "",
            item.get("quality_grade") or "",
        ),
    )[:limit]
    _attach_farmer_reports(db, crop, board)
    return board


def _attach_farmer_reports(db: Session, crop: str, board: list[dict]) -> None:
    if not board:
        return
    region_ids = {row.get("region_id") for row in board if row.get("region_id")}
    variety_ids = {row.get("variety_id") for row in board if row.get("variety_id")}
    if not region_ids or not variety_ids:
        return

    reports = db.scalars(
        select(UserPriceReport)
        .where(UserPriceReport.crop_type == crop)
        .where(UserPriceReport.region_id.in_(region_ids))
        .where(UserPriceReport.variety_id.in_(variety_ids))
        .order_by(desc(UserPriceReport.created_at))
    ).all()
    exact: dict[tuple[int, int, str | None], UserPriceReport] = {}
    fallback: dict[tuple[int, int], UserPriceReport] = {}
    for report in reports:
        fallback.setdefault((report.region_id, report.variety_id), report)
        exact.setdefault((report.region_id, report.variety_id, report.quality_grade), report)

    for row in board:
        region_id = row.get("region_id")
        variety_id = row.get("variety_id")
        if not region_id or not variety_id:
            continue
        report = exact.get((region_id, variety_id, row.get("quality_grade"))) or fallback.get((region_id, variety_id))
        if report is None:
            row["farmer_report_price_vnd"] = None
            row["farmer_reported_at"] = None
            row["farmer_report_quality_grade"] = None
            continue
        row["farmer_report_price_vnd"] = float(report.price_vnd)
        row["farmer_reported_at"] = report.created_at
        row["farmer_report_quality_grade"] = report.quality_grade


@router.get("/analytics/historical-prices", response_model=list[HistoricalPricePoint])
def historical_prices(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=None),
    quality_grade: str | None = Query(default=None),
    limit: int = Query(default=180, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict]:
    return DataLoader(db).historical_prices(
        region_id=region_id,
        variety_id=variety_id or variety,
        crop_type=crop,
        quality_grade=quality_grade,
        limit=limit,
    )


@router.get("/analytics/forecast-30-days", response_model=list[ForecastPoint])
@cached(prefix="forecast", ttl_seconds=1800)
def forecast_30_days(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=1),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=1),
    db: Session = Depends(get_db),
) -> list[dict]:
    config = ForecastConfig()
    loader = DataLoader(db)
    window = loader.latest_feature_window(crop_type=crop, region_id=region_id, variety_id=variety_id or variety)
    forecasts = LSTMForecaster(config).predict_30_days(window)
    if not window:
        return []
    timestamps = loader.extend_timestamps(window[-1]["timestamp"], config.horizon_days)
    latest_price = float(window[-1].get("max_price_vnd") or forecasts[0] or 0)
    price_scaled_band = max(450.0 if crop == "lua" else 2500.0, latest_price * (0.08 if crop != "lua" else 0.055))
    band = min(config.rmse_usd_per_kg * 24500, price_scaled_band)
    return [
        {
            "timestamp": ts,
            "forecast_price_vnd": price,
            "confidence_low_vnd": round(price - band, 2),
            "confidence_high_vnd": round(price + band, 2),
        }
        for ts, price in zip(timestamps, forecasts, strict=False)
    ]


@router.get("/analytics/trading-signals", response_model=list[TradingSignal])
def trading_signals(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=1),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=1),
    db: Session = Depends(get_db),
) -> list[dict]:
    points = DataLoader(db).historical_prices(
        crop_type=crop, region_id=region_id, variety_id=variety_id or variety, limit=180
    )
    return detect_optimal_sell_points(points)


@router.get("/analytics/model-metrics", response_model=ModelMetrics)
def model_metrics(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ModelMetrics:
    latest_run = db.scalar(
        select(ModelTrainingRun)
        .where(ModelTrainingRun.crop_type == crop)
        .order_by(desc(ModelTrainingRun.started_at))
        .limit(1)
    )
    if latest_run is None:
        return ModelMetrics(note="Chưa có backtest. Job retrain sẽ chạy theo lịch.")
    rmse_vnd = float(latest_run.rmse_vnd_per_kg) if latest_run.rmse_vnd_per_kg else None
    mae_vnd = float(latest_run.mae_vnd_per_kg) if latest_run.mae_vnd_per_kg else None
    return ModelMetrics(
        rmse_vnd_per_kg=rmse_vnd,
        mae_vnd_per_kg=mae_vnd,
        rmse_usd_per_kg=round(rmse_vnd / 24500, 4) if rmse_vnd else 0.45,
        mae_usd_per_kg=round(mae_vnd / 24500, 4) if mae_vnd else 0.32,
        lookback_days=60,
        forecast_horizon_days=30,
        backtest_samples=latest_run.backtest_samples,
        evaluated_series=latest_run.evaluated_series,
        note=latest_run.note,
    )


@router.get("/analytics/data-quality")
@cached(prefix="data-quality", ttl_seconds=600)
def data_quality(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return MarketIntelligenceService(db).data_quality(crop=crop, region_id=region_id, variety_id=variety_id or variety)


@router.get("/analytics/source-health")
def source_health(crop: str = Query(default="sau_rieng"), db: Session = Depends(get_db)) -> list[dict]:
    return MarketIntelligenceService(db).source_health(crop=crop)


@router.get("/analytics/top-movers")
@cached(prefix="top-movers", ttl_seconds=600)
def top_movers(
    crop: str = Query(default="sau_rieng"),
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db),
) -> dict:
    return MarketIntelligenceService(db).top_movers(crop=crop, limit=limit)


@router.get("/analytics/heatmap")
@cached(prefix="heatmap", ttl_seconds=600)
def heatmap(crop: str = Query(default="sau_rieng"), db: Session = Depends(get_db)) -> list[dict]:
    return MarketIntelligenceService(db).heatmap(crop=crop)


@router.get("/analytics/strategy-alerts")
def strategy_alerts(
    crop: str = Query(default="sau_rieng"),
    region_id: int = Query(default=1),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=1),
    db: Session = Depends(get_db),
) -> list[dict]:
    return MarketIntelligenceService(db).alerts(crop=crop, region_id=region_id, variety_id=variety_id or variety or 1)


@router.get("/analytics/market-index")
@cached(prefix="market-index", ttl_seconds=600)
def market_index(crop: str = Query(default="sau_rieng"), db: Session = Depends(get_db)) -> dict:
    return MarketIntelligenceService(db).market_index(crop=crop)


@router.get("/analytics/explain-change")
def explain_change(
    crop: str = Query(default="sau_rieng"),
    region_id: int = Query(default=1),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=1),
    db: Session = Depends(get_db),
) -> dict:
    return MarketIntelligenceService(db).explain_change(
        crop=crop,
        region_id=region_id,
        variety_id=variety_id or variety or 1,
    )


@router.get("/analytics/compare-markets")
@cached(prefix="compare-markets", ttl_seconds=600)
def compare_markets(
    crop: str = Query(default="sau_rieng"),
    region_id: int = Query(default=1),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=1),
    db: Session = Depends(get_db),
) -> dict:
    return MarketIntelligenceService(db).compare_markets(
        crop=crop,
        region_id=region_id,
        variety_id=variety_id or variety or 1,
    )


@router.get("/analytics/export.csv")
def export_csv(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    body = MarketIntelligenceService(db).export_csv(crop=crop, region_id=region_id, variety_id=variety_id or variety)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="market-data.csv"'},
    )


@router.get("/analytics/export.xlsx")
def export_xlsx(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    rows = DataLoader(db).historical_prices(
        crop_type=crop,
        region_id=region_id,
        variety_id=variety_id or variety,
        quality_grade=None,
        limit=1000,
    )
    return Response(
        content=rows_to_xlsx(rows, sheet_name="Gia nong san"),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="market-data.xlsx"'},
    )


@router.get("/analytics/export.pdf")
def export_pdf(
    crop: str = Query(default="sau_rieng"),
    region_id: int | None = Query(default=None),
    variety_id: int | None = Query(default=None),
    variety: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    rows = DataLoader(db).historical_prices(
        crop_type=crop,
        region_id=region_id,
        variety_id=variety_id or variety,
        quality_grade=None,
        limit=1000,
    )
    return Response(
        content=rows_to_pdf(rows),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="market-report.pdf"'},
    )
