from __future__ import annotations

import html
import json
import logging
from typing import Any

import requests

from app.core.config import get_settings


logger = logging.getLogger(__name__)
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}
SEVERITY_EMOJI = {"info": "i", "warning": "!", "error": "ERROR", "critical": "CRITICAL"}


def send_ops_alert(
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    severity: str | None = None,
    context: dict[str, Any] | None = None,
    message: str | None = None,
) -> bool:
    """Send an ops alert to Telegram when configured, with webhook fallback.

    The positional event/payload signature is kept for existing job code and tests.
    """
    settings = get_settings()
    alert_severity = _normalize_severity(severity or _infer_severity(event, payload))
    if not _severity_enabled(alert_severity, settings.telegram_min_severity):
        return False

    alert_context: dict[str, Any] = {}
    if payload:
        alert_context.update(payload)
    if context:
        alert_context.update(context)
    alert_message = message or event.replace("_", " ")

    if settings.telegram_bot_token and settings.telegram_chat_id:
        return _send_telegram(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            message=alert_message,
            severity=alert_severity,
            context=alert_context,
            timeout=settings.ops_alert_timeout_seconds,
        )

    webhook_url = settings.ops_alert_webhook_url.strip()
    if webhook_url:
        return _send_generic_webhook(
            webhook_url,
            event=event,
            message=alert_message,
            severity=alert_severity,
            context=alert_context,
            timeout=settings.ops_alert_timeout_seconds,
        )

    logger.warning("ops_alert_skipped_no_channel event=%s", event)
    return False


def _normalize_severity(value: str) -> str:
    severity = value.strip().lower()
    return severity if severity in SEVERITY_ORDER else "warning"


def _infer_severity(event: str, payload: dict[str, Any] | None) -> str:
    text = f"{event} {json.dumps(payload or {}, default=str, ensure_ascii=False)}".lower()
    if "critical" in text or "fatal" in text:
        return "critical"
    if "failed" in text or "error" in text or "exception" in text:
        return "error"
    return "warning"


def _severity_enabled(severity: str, minimum: str) -> bool:
    minimum_normalized = _normalize_severity(minimum or "info")
    return SEVERITY_ORDER[severity] >= SEVERITY_ORDER[minimum_normalized]


def _send_telegram(
    *,
    token: str,
    chat_id: str,
    message: str,
    severity: str,
    context: dict[str, Any],
    timeout: float,
) -> bool:
    emoji = SEVERITY_EMOJI.get(severity, "ALERT")
    text = f"{emoji} <b>{html.escape(severity.upper())}</b>\n\n{html.escape(message)}"
    if context:
        context_json = json.dumps(context, ensure_ascii=False, default=str, indent=2)
        text += "\n\n<pre>" + html.escape(context_json[:3200]) + "</pre>"
    if len(text) > 3900:
        text = text[:3890] + "...[truncated]"

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=max(0.5, timeout),
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("telegram_ops_alert_failed")
        return False


def _send_generic_webhook(
    url: str,
    *,
    event: str,
    message: str,
    severity: str,
    context: dict[str, Any],
    timeout: float,
) -> bool:
    try:
        response = requests.post(
            url,
            json={"event": event, "text": f"[{severity.upper()}] {message}", "context": context},
            timeout=max(0.5, timeout),
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception("generic_ops_alert_failed event=%s", event)
        return False
