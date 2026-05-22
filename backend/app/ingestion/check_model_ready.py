import sys

from app.db import SessionLocal, init_db
from app.main import _is_production_region
from app.ml_engine.evaluator import ForecastEvaluator
from app.ml_engine.lstm_forecaster import ForecastConfig, LSTMForecaster
from app.models import DailyMarketPrice, DurianVariety, ProductionRegion
from app.services.data_loader import DataLoader
from sqlalchemy import select


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    crop_type = sys.argv[1] if len(sys.argv) > 1 else "sau_rieng"
    init_db()
    failures = []
    with SessionLocal() as db:
        regions = [
            row
            for row in db.scalars(select(ProductionRegion).order_by(ProductionRegion.region_id)).all()
            if _is_production_region(row)
            and db.scalar(
                select(DailyMarketPrice.id)
                .where(DailyMarketPrice.region_id == row.region_id)
                .where(DailyMarketPrice.crop_type == crop_type)
                .limit(1)
            )
        ]
        varieties = db.scalars(select(DurianVariety).order_by(DurianVariety.variety_id)).all()
        varieties = [variety for variety in varieties if variety.crop_type == crop_type]
        loader = DataLoader(db)
        for region in regions:
            for variety in varieties:
                history = loader.historical_prices(
                    region_id=region.region_id,
                    variety_id=variety.variety_id,
                    crop_type=crop_type,
                    quality_grade="Loại A",
                    limit=180,
                )
                forecast = LSTMForecaster(
                    ForecastConfig(),
                    crop_type=crop_type,
                    region_id=region.region_id,
                    variety_id=variety.variety_id,
                ).predict_30_days(
                    loader.latest_feature_window(
                        region_id=region.region_id,
                        variety_id=variety.variety_id,
                        crop_type=crop_type,
                    )
                )
                metrics = ForecastEvaluator(
                    db,
                    crop_type=crop_type,
                    region_id=region.region_id,
                    variety_id=variety.variety_id,
                ).backtest()
                if (
                    len(history) < 67
                    or len(forecast) != 30
                    or metrics.get("backtest_samples", 0) == 0
                    or metrics.get("rmse_vnd_per_kg") is None
                ):
                    failures.append(
                        {
                            "province": region.province,
                            "variety": variety.name,
                            "history_points": len(history),
                            "forecast_points": len(forecast),
                            "backtest_samples": metrics.get("backtest_samples", 0),
                            "rmse_vnd_per_kg": metrics.get("rmse_vnd_per_kg"),
                        }
                    )
        print(f"regions={len(regions)} varieties={len(varieties)} pairs={len(regions) * len(varieties)}")
        print(f"failures={len(failures)}")
        for item in failures[:20]:
            print(item)


if __name__ == "__main__":
    main()
