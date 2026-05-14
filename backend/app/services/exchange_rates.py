from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import time
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests


logger = logging.getLogger(__name__)

VCB_EXCHANGE_RATE_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
_CACHE_TTL_SECONDS = 10 * 60
_CACHE: tuple[dict, float] | None = None
_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


@dataclass(frozen=True)
class UsdVndRate:
    currency_code: str
    buy: float | None
    transfer: float
    sell: float | None
    as_of: datetime | None
    source: str
    raw_datetime: str | None

    def as_dict(self) -> dict:
        return {
            "currency_code": self.currency_code,
            "buy": self.buy,
            "transfer": self.transfer,
            "sell": self.sell,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "source": self.source,
            "raw_datetime": self.raw_datetime,
        }


def fetch_usd_vnd_rate() -> dict:
    global _CACHE
    now = time.time()
    if _CACHE and now < _CACHE[1]:
        return _CACHE[0]

    try:
        rate = _fetch_vcb_usd_vnd_rate().as_dict()
        _CACHE = (rate, now + _CACHE_TTL_SECONDS)
        return rate
    except Exception:
        logger.exception("Could not fetch USD/VND rate from Vietcombank")
        if _CACHE:
            return {**_CACHE[0], "stale": True}
        raise


def _fetch_vcb_usd_vnd_rate() -> UsdVndRate:
    response = requests.get(VCB_EXCHANGE_RATE_URL, timeout=12)
    response.raise_for_status()
    root = ElementTree.fromstring(response.content)
    raw_datetime = root.findtext("DateTime")
    as_of = _parse_vcb_datetime(raw_datetime)

    for item in root.findall("Exrate"):
        if item.attrib.get("CurrencyCode") != "USD":
            continue
        transfer = _parse_rate(item.attrib.get("Transfer"))
        if transfer is None:
            raise ValueError("Vietcombank USD transfer rate is missing")
        return UsdVndRate(
            currency_code="USD",
            buy=_parse_rate(item.attrib.get("Buy")),
            transfer=transfer,
            sell=_parse_rate(item.attrib.get("Sell")),
            as_of=as_of,
            source="Vietcombank",
            raw_datetime=raw_datetime,
        )

    raise ValueError("USD rate not found in Vietcombank XML")


def _parse_rate(value: str | None) -> float | None:
    if not value or value.strip() == "-":
        return None
    return float(value.replace(",", "").strip())


def _parse_vcb_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%d/%m/%Y %I:%M:%S %p"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=_TZ)
        except ValueError:
            continue
    return None
