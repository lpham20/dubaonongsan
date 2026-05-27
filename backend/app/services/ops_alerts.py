from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.core.config import get_settings


logger = logging.getLogger(__name__)


def send_ops_alert(event: str, payload: dict) -> bool:
    settings = get_settings()
    webhook_url = settings.ops_alert_webhook_url.strip()
    if not webhook_url:
        return False

    body = json.dumps({"event": event, "payload": payload}, ensure_ascii=False, default=str).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "MarketAI-OpsAlert/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=max(0.5, settings.ops_alert_timeout_seconds)) as response:
            status = int(getattr(response, "status", 200))
            return 200 <= status < 300
    except (OSError, urllib.error.URLError):
        logger.exception("ops_alert_failed event=%s", event)
        return False
