from datetime import UTC, datetime

from app.ingestion.sources.world_fertilizer_commoditypriceapi import (
    CommodityPriceApiUreaPublicScraper,
    parse_commoditypriceapi_urea_history,
    parse_next_action_id,
    parse_next_action_payload,
    parse_public_latest_quote,
)
from app.ingestion.world_fertilizer_registry import build_world_fertilizer_scrapers


def test_commoditypriceapi_parser_reads_public_ohlc_history():
    rows = parse_commoditypriceapi_urea_history(
        {
            "success": True,
            "startDate": "2025-05-24",
            "endDate": "2026-05-24",
            "rates": {
                "2026-05-22": {"UREA": {"open": 542.5, "high": 502.5, "low": 502.5, "close": 502.5}},
                "bad": {"UREA": {"close": 999}},
                "2026-05-23": {"OTHER": {"close": 1}},
            },
        }
    )

    assert len(rows) == 1
    assert rows[0].observed_at == datetime(2026, 5, 22, tzinfo=UTC)
    assert rows[0].price_usd_per_tonne == 502.5
    assert rows[0].source == "commoditypriceapi_urea_public_1y"
    assert rows[0].raw_json["symbol"] == "UREA"


def test_commoditypriceapi_next_action_helpers_parse_rsc_payload():
    html = r'18:{\"id\":\"604a8062e6bd4d48ec8e1004dbc4ae94a5bdaa5636\",\"bound\":null}\n...\"timeSeriesData\":\"$h18\"'
    text = (
        '0:{"a":"$@1","f":"","q":"","i":false,"b":"test"}\n'
        '1:{"success":true,"rates":{"2026-05-22":{"UREA":{"close":502.5}}}}\n'
    )

    assert parse_next_action_id(html) == "604a8062e6bd4d48ec8e1004dbc4ae94a5bdaa5636"
    assert parse_next_action_payload(text)["rates"]["2026-05-22"]["UREA"]["close"] == 502.5


def test_commoditypriceapi_latest_quote_reads_embedded_page_price():
    html = r'\"prices\":{\"success\":true,\"timestamp\":1779634510,\"rates\":{\"UREA\":502.5},\"metadata\":{}}'

    row = parse_public_latest_quote(html)

    assert row is not None
    assert row.price_usd_per_tonne == 502.5
    assert row.observed_at == datetime(2026, 5, 24, tzinfo=UTC)


def test_commoditypriceapi_scraper_fetches_action_and_history(monkeypatch):
    captured = {}

    class Response:
        def __init__(self, text):
            self.text = text

        @staticmethod
        def raise_for_status():
            return None

    page_html = (
        r'18:{\"id\":\"604a8062e6bd4d48ec8e1004dbc4ae94a5bdaa5636\",\"bound\":null}'
        r'\"timeSeriesData\":\"$h18\"'
    )
    action_text = (
        '0:{"a":"$@1","f":"","q":"","i":false,"b":"test"}\n'
        '1:{"success":true,"rates":{"2026-05-22":{"UREA":{"close":502.5}}}}\n'
    )

    def fake_get(url, *, headers, timeout):
        captured["get"] = {"url": url, "headers": headers, "timeout": timeout}
        return Response(page_html)

    def fake_post(url, *, data, headers, timeout):
        captured["post"] = {"url": url, "data": data, "headers": headers, "timeout": timeout}
        return Response(action_text)

    import app.ingestion.sources.world_fertilizer_commoditypriceapi as commoditypriceapi

    monkeypatch.setattr(commoditypriceapi.requests, "get", fake_get)
    monkeypatch.setattr(commoditypriceapi.requests, "post", fake_post)

    result = CommodityPriceApiUreaPublicScraper().scrape()

    assert result.observations[0].price_usd_per_tonne == 502.5
    assert captured["post"]["headers"]["Next-Action"] == "604a8062e6bd4d48ec8e1004dbc4ae94a5bdaa5636"
    assert captured["post"]["data"] == '[365, "UREA"]'


def test_commoditypriceapi_source_is_explicitly_registered():
    default_sources = [scraper.source for scraper in build_world_fertilizer_scrapers()]
    explicitly_selected = build_world_fertilizer_scrapers(source="commoditypriceapi_urea_public_1y")

    assert "commoditypriceapi_urea_public_1y" not in default_sources
    assert explicitly_selected[0].source == "commoditypriceapi_urea_public_1y"
