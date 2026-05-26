import logging
import re

from fastapi import APIRouter, Request, Response

from app.core.config import get_settings


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["security"])
logger = logging.getLogger("marketai.security")

_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


@router.post("/csp-report", include_in_schema=False)
async def csp_report(request: Request) -> Response:
    try:
        body = await request.json()
    except Exception:
        body = (await request.body()).decode("utf-8", errors="replace")[:2000]
    logger.warning("csp_violation body=%s", _redact_report(body))
    return Response(status_code=204)


def _redact_report(value) -> str:
    text = str(value)
    text = _URL_RE.sub("[redacted-url]", text)
    return text[:1000]
