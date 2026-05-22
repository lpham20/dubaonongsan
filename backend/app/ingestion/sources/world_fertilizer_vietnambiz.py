from __future__ import annotations

from datetime import UTC, datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

from app.ingestion.http import fetch_html
from app.ingestion.world_fertilizer_records import WorldFertilizerObservation, WorldFertilizerScrapeResult


SOURCE = "vietnambiz_world_fertilizer"
PAGE_URL = "https://vietnambiz.vn/hang-hoa/phan-bon.htm"
ARTICLE_LIMIT = 12

PRICE_RE = re.compile(
    r"(?P<name>ur[eê]|urea|dap|kali|mop|potassium|kcl)"
    r"(?P<context>.{0,180}?)"
    r"(?P<price>\d{2,4}(?:[.,]\d{1,2})?)\s*(?:usd|us\$|\$)\s*/\s*(?:tấn|tan|tonne|mt|t)",
    flags=re.IGNORECASE | re.DOTALL,
)


class VietnamBizWorldFertilizerScraper:
    source = SOURCE
    source_url = PAGE_URL

    def scrape(self) -> WorldFertilizerScrapeResult:
        observations: list[WorldFertilizerObservation] = []
        try:
            index_html = fetch_html(PAGE_URL)
        except requests.RequestException:
            return WorldFertilizerScrapeResult(source=self.source, source_url=self.source_url, observations=observations)
        for url in self._extract_article_urls(index_html):
            try:
                html = fetch_html(url)
            except requests.RequestException:
                continue
            published_at = self._published_at(html)
            observations.extend(self._parse_article(html, published_at, url))
        return WorldFertilizerScrapeResult(source=self.source, source_url=self.source_url, observations=observations)

    def _extract_article_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            text = link.get_text(" ", strip=True).lower()
            if "phân bón" not in text and "phan-bon" not in href:
                continue
            url = urljoin(PAGE_URL, href)
            if "vietnambiz.vn" not in url or url in urls:
                continue
            urls.append(url)
            if len(urls) >= ARTICLE_LIMIT:
                break
        return urls

    def _published_at(self, html: str) -> datetime:
        soup = BeautifulSoup(html, "html.parser")
        for attrs in (
            {"property": "article:published_time"},
            {"name": "pubdate"},
            {"itemprop": "datePublished"},
        ):
            meta = soup.find("meta", attrs=attrs)
            content = meta.get("content") if meta else None
            if not content:
                continue
            try:
                return datetime.fromisoformat(content.replace("Z", "+00:00")).astimezone(UTC)
            except ValueError:
                continue
        return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    def _parse_article(self, html: str, published_at: datetime, url: str) -> list[WorldFertilizerObservation]:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        observations: list[WorldFertilizerObservation] = []
        seen: set[tuple[str, str, float]] = set()
        for match in PRICE_RE.finditer(text):
            commodity_slug, quote_type = _commodity_from_text(match.group("name"), match.group("context"))
            price = _parse_price(match.group("price"))
            if commodity_slug is None or price is None or not 100 <= price <= 1500:
                continue
            key = (commodity_slug, quote_type, price)
            if key in seen:
                continue
            seen.add(key)
            observations.append(
                WorldFertilizerObservation(
                    observed_at=published_at,
                    commodity_slug=commodity_slug,
                    quote_type=quote_type,
                    source=SOURCE,
                    source_url=url,
                    price_usd_per_tonne=price,
                    confidence_score=0.72,
                    raw_json={"snippet": match.group(0)[:220]},
                )
            )
        return observations


def _commodity_from_text(name: str, context: str) -> tuple[str | None, str]:
    text = f"{name} {context}".lower()
    if "dap" in text:
        return "dap", "FOB/CFR public news"
    if any(term in text for term in ("kali", "mop", "potassium", "kcl")):
        return "kali_mop", "FOB/CFR public news"
    if any(term in text for term in ("urea", "ure", "urê")):
        quote_type = "CFR China" if "china" in text or "trung quốc" in text else "FOB/CFR public news"
        return "urea", quote_type
    return None, "public news"


def _parse_price(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None
