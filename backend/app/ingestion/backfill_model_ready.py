import sys

from app.db import SessionLocal, init_db
from app.services.model_ready_backfill import ModelReadyBackfillService


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    crop_type = sys.argv[1] if len(sys.argv) > 1 else "sau_rieng"
    init_db()
    with SessionLocal() as db:
        summary = ModelReadyBackfillService(db, crop_type=crop_type).backfill()
        print(
            f"{summary['source']}: {summary['status']} "
            f"found={summary['records_found']} "
            f"inserted={summary['records_inserted']} "
            f"updated={summary['records_updated']} "
            f"model_ready_pairs={summary['model_ready_pairs']}"
        )


if __name__ == "__main__":
    main()
