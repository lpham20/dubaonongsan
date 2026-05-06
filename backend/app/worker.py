from __future__ import annotations

import logging
import signal
import sys
import threading

from app.core.config import get_settings
from app.db import SessionLocal, init_db
from app.seed import normalize_vietnamese_labels, seed_database
from app.services.content_portal import ContentPortalService
from app.services.crop_catalog import ensure_crop_catalog
from app.services.platform_jobs import JobScheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
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
        content = ContentPortalService(db)
        content.seed_guides()
        content.seed_fallback_news()


def main() -> None:
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    bootstrap()
    JobScheduler.start_once()
    logger.info("MarketAI worker started. Scheduled scrape/news/data-quality/retrain jobs are active.")
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
