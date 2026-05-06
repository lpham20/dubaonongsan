import sys

from app.db import SessionLocal, init_db
from app.ingestion.service import PriceIngestionService


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    init_db()
    with SessionLocal() as db:
        summaries = PriceIngestionService(db).scrape_and_store()
        for summary in summaries:
            print(
                f"{summary['source']}: {summary['status']} "
                f"found={summary.get('records_found', 0)} "
                f"inserted={summary.get('records_inserted', 0)} "
                f"updated={summary.get('records_updated', 0)}"
            )


if __name__ == "__main__":
    main()
