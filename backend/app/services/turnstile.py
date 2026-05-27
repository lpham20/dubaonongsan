from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import get_settings


logger = logging.getLogger(__name__)


def verify_turnstile_token(token: str, remote_ip: str | None = None) -> bool:
    settings = get_settings()
    secret = settings.turnstile_secret_key.strip()
    if not secret:
        return False

    form = {
        "secret": secret,
        "response": token,
    }
    if remote_ip:
        form["remoteip"] = remote_ip
    body = urllib.parse.urlencode(form).encode("utf-8")
    request = urllib.request.Request(
        settings.turnstile_verify_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "MarketAI-Turnstile/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        logger.exception("turnstile_verification_failed")
        return False
    return bool(payload.get("success"))
