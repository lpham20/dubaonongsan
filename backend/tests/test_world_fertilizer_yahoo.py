from datetime import UTC, datetime

import app.ingestion.sources.world_fertilizer_yahoo as yahoo
from app.ingestion.sources.world_fertilizer_yahoo import YahooUreaFuturesDailyScraper, parse_yahoo_urea_chart
from app.ingestion.world_fertilizer_registry import build_world_fertilizer_scrapers


def test_yahoo_urea_parser_reads_daily_close_and_skips_empty_values():
    rows = parse_yahoo_urea_chart(
        {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": "UME=F", "exchangeName": "CBT", "instrumentType": "FUTURE"},
                        "timestamp": [1_717_286_400, 1_717_372_800, 1_717_459_200],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [500.0, 501.0, 502.0],
                                    "high": [505.0, 506.0, 507.0],
                                    "low": [498.0, 499.0, 500.0],
                                    "close": [502.5, None, 504.25],
                                    "volume": [0, 0, 12],
                                }
                            ]
                        },
                    }
                ],
                "error": None,
            }
        },
        symbol="UME=F",
    )

    assert [row.observed_at for row in rows] == [
        datetime(2024, 6, 2, tzinfo=UTC),
        datetime(2024, 6, 4, tzinfo=UTC),
    ]
    assert rows[0].commodity_slug == "urea"
    assert rows[0].quote_type == "CME Urea Granular FOB Middle East futures continuous"
    assert rows[0].source == "yahoo_urea_futures_daily"
    assert rows[1].price_usd_per_tonne == 504.25
    assert rows[1].raw_json["symbol"] == "UME=F"


def test_yahoo_urea_scraper_uses_configurable_symbol_without_credentials(monkeypatch):
    captured = {}

    class Response:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {
                "chart": {
                    "result": [
                        {
                            "meta": {"symbol": "UME=F", "exchangeName": "CBT"},
                            "timestamp": [1_717_286_400],
                            "indicators": {"quote": [{"close": [502.5]}]},
                        }
                    ]
                }
            }

    def fake_get(url, *, params, headers, timeout):
        captured.update({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return Response()

    monkeypatch.setenv("MARKETAI_YAHOO_UREA_SYMBOL", "UME=F")
    monkeypatch.setenv("MARKETAI_YAHOO_UREA_RANGE", "1y")
    monkeypatch.setattr(yahoo.requests, "get", fake_get)

    result = YahooUreaFuturesDailyScraper().scrape()

    assert result.observations[0].price_usd_per_tonne == 502.5
    assert captured["url"].endswith("/UME%3DF")
    assert captured["params"]["range"] == "1y"
    assert captured["params"]["interval"] == "1d"
    assert "Authorization" not in captured["headers"]


def test_yahoo_urea_source_is_manual_until_scheduled_later():
    default_sources = [scraper.source for scraper in build_world_fertilizer_scrapers()]
    explicitly_selected = build_world_fertilizer_scrapers(source="yahoo_urea_futures_daily")

    assert "yahoo_urea_futures_daily" not in default_sources
    assert explicitly_selected[0].source == "yahoo_urea_futures_daily"
