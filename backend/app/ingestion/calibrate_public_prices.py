import sys

from app.db import SessionLocal, init_db
from app.services.crop_catalog import CROP_TYPES, ensure_crop_catalog
from app.services.model_ready_backfill import ModelReadyBackfillService
from app.services.public_price_calibration import PublicPriceCalibrationService


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    crop_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    crops = list(CROP_TYPES) if crop_type == "all" else [crop_type]
    init_db()
    with SessionLocal() as db:
        ensure_crop_catalog(db)
        for crop in crops:
            backfill = ModelReadyBackfillService(db, crop_type=crop).backfill()
            summary = PublicPriceCalibrationService(db, crop_type=crop).calibrate()
            print(
                f"{crop}: backfill_inserted={backfill['records_inserted']} "
                f"calibrated={summary['calibrated_rows']} "
                f"inserted={summary['inserted_rows']} updated={summary['updated_rows']} "
                f"pairs={summary['production_pairs']} sources={summary['source_count']}"
            )


if __name__ == "__main__":
    main()
