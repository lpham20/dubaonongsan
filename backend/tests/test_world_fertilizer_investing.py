from datetime import UTC, datetime

from app.ingestion.sources.world_fertilizer_investing import READER_URL, SOURCE_URL, parse_investing_urea_current
from app.ingestion.world_fertilizer_registry import build_world_fertilizer_scrapers


def test_investing_urea_parser_reads_current_price_and_observed_date():
    markdown = """
# Urea Granular FOB Middle East Futures - (UMEc1)

Thong tin tai chinh chi tiet.

CME

Tien te tinh theo USD

Them vao Danh Muc

732.50

-13.50(-1.81%)

Dong cua·22/05

Bien do ngay
"""

    row = parse_investing_urea_current(markdown, fetched_at=datetime(2026, 5, 24, 4, tzinfo=UTC))

    assert row.commodity_slug == "urea"
    assert row.source == "investing_urea_current"
    assert row.price_usd_per_tonne == 732.5
    assert row.observed_at == datetime(2026, 5, 22, tzinfo=UTC)
    assert row.raw_json["symbol"] == "UMEc1"
    assert row.raw_json["change_pct"] == -1.81


def test_investing_reader_url_has_single_scheme():
    assert READER_URL == f"https://r.jina.ai/{SOURCE_URL}"
    assert "http://https://" not in READER_URL


def test_investing_urea_source_is_selectable_but_not_default():
    default_sources = [scraper.source for scraper in build_world_fertilizer_scrapers()]
    explicitly_selected = build_world_fertilizer_scrapers(source="investing_urea_current")

    assert "investing_urea_current" not in default_sources
    assert explicitly_selected[0].source == "investing_urea_current"
