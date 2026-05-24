from datetime import UTC, datetime

import app.ingestion.sources.world_fertilizer_tradingeconomics as tradingeconomics
from app.ingestion.sources.world_fertilizer_tradingeconomics import (
    TradingEconomicsUreaDailyScraper,
    parse_trading_economics_urea_history,
)
from app.ingestion.world_fertilizer_registry import build_world_fertilizer_scrapers


def test_tradingeconomics_urea_parser_reads_daily_close_and_sorts_dates():
    rows = parse_trading_economics_urea_history(
        [
            {"Symbol": "UREA:COM", "Date": "22/05/2026", "Open": 510, "High": 515, "Low": 500, "Close": 502.5},
            {"Symbol": "UREA:COM", "Date": "2026-05-21T00:00:00", "Open": 530, "High": 540, "Low": 510, "Close": 512.5},
            {"Symbol": "UREA:COM", "Date": "invalid", "Close": 999},
            {"Symbol": "UREA:COM", "Date": "20/05/2026", "Close": None},
        ]
    )

    assert [row.observed_at for row in rows] == [
        datetime(2026, 5, 21, tzinfo=UTC),
        datetime(2026, 5, 22, tzinfo=UTC),
    ]
    assert rows[-1].commodity_slug == "urea"
    assert rows[-1].price_usd_per_tonne == 502.5
    assert rows[-1].source == "tradingeconomics_urea_daily"


def test_tradingeconomics_urea_scraper_keeps_api_key_out_of_url(monkeypatch):
    captured = {}

    class Response:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return [{"Symbol": "UREA:COM", "Date": "22/05/2026", "Close": 502.5}]

    def fake_get(url, *, params, headers, timeout):
        captured.update({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return Response()

    start_date = datetime.now(UTC).date().isoformat()
    monkeypatch.setenv("MARKETAI_TRADING_ECONOMICS_API_KEY", "secret-test-key")
    monkeypatch.setenv("MARKETAI_TRADING_ECONOMICS_UREA_BACKFILL_START", start_date)
    monkeypatch.setattr(tradingeconomics.requests, "get", fake_get)

    result = TradingEconomicsUreaDailyScraper().scrape()

    assert result.observations[0].price_usd_per_tonne == 502.5
    assert captured["headers"]["Authorization"] == "secret-test-key"
    assert "c" not in captured["params"]
    assert "secret-test-key" not in captured["url"]
    assert captured["params"]["d1"] == start_date


def test_tradingeconomics_urea_source_is_opt_in_until_configured():
    default_sources = [scraper.source for scraper in build_world_fertilizer_scrapers()]
    explicitly_selected = build_world_fertilizer_scrapers(source="tradingeconomics_urea_daily")

    assert "tradingeconomics_urea_daily" not in default_sources
    assert explicitly_selected[0].source == "tradingeconomics_urea_daily"
