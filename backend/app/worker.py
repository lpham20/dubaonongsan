from __future__ import annotations

import logging
import signal
import sys
import threading
from datetime import datetime, timezone

from sqlalchemy import desc, select

from app.core.config import get_settings
from app.db import SessionLocal, init_db
from app.models import ScrapeRun
from app.seed import normalize_vietnamese_labels, seed_database
from app.services.content_portal import ContentPortalService
from app.services.crop_catalog import ensure_crop_catalog
from app.services.input_prices import seed_input_prices
from app.services.platform_jobs import JobScheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)
logger = logging.getLogger("marketai.worker")
shutdown_event = threading.Event()


def bootstrap() -> None:
    settings = get_settings()
    init_db()
    if not settings.seed_on_startup:
        return

    with SessionLocal() as db:
        seed_database(db)
        normalize_vietnamese_labels(db)
        ensure_crop_catalog(db)
        seed_input_prices(db)
        content = ContentPortalService(db)
        content.seed_guides()
        content.seed_fallback_news()


def main() -> None:
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    bootstrap()
    settings = get_settings()
    try:
        with SessionLocal() as db:
            last = db.scalar(
                select(ScrapeRun.finished_at)
                .where(ScrapeRun.status.in_(["thành công", "trùng lặp", "trống"]))
                .where(ScrapeRun.finished_at.is_not(None))
                .order_by(desc(ScrapeRun.finished_at))
                .limit(1)
            )
            if last:
                last_utc = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
                gap_hours = (datetime.now(timezone.utc) - last_utc).total_seconds() / 3600
                if gap_hours > 4:
                    logger.warning(
                        "WORKER WAKE-UP: last completed scrape was %.1f hours ago - there was downtime",
                        gap_hours,
                    )
    except Exception:
        logger.exception("Could not check last-scrape gap on boot")

    JobScheduler.start_once()
    logger.info(
        "MarketAI worker started. Scheduled price/input-price/news/data-quality/retrain jobs are active. "
        "scrape_interval=%d min, news_interval=%d min",
        settings.scrape_interval_minutes,
        settings.news_scrape_interval_minutes,
    )
    shutdown_event.wait()
    logger.info("Stopping job scheduler...")
    JobScheduler.shutdown()
    logger.info("Worker stopped cleanly.")
    sys.exit(0)


def handle_shutdown(signum, frame) -> None:
    logger.info("Received shutdown signal %s, stopping worker...", signum)
    shutdown_event.set()


if __name__ == "__main__":
    main()
