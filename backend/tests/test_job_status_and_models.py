from datetime import UTC, datetime

import pytest

from app.core.job_status import STATUS_DUPLICATE, STATUS_SUCCESS, is_success_status
from app.models import RecommendationSession, WorldCommodityForecast


def test_job_status_accepts_canonical_and_legacy_success_values():
    assert is_success_status(STATUS_SUCCESS)
    assert is_success_status(STATUS_DUPLICATE)
    assert is_success_status("thanh cong")
    assert is_success_status("th\u00e0nh c\u00f4ng")
    assert not is_success_status("failed")


def test_world_commodity_forecast_points_are_validated():
    forecast = WorldCommodityForecast(
        commodity_slug="urea",
        generated_at=datetime.now(UTC),
        horizon_days=1,
        forecast_points_json=[{"date": "2026-05-27", "price_usd_per_tonne": 503.2}],
        model_kind="test",
        base_price_usd_per_tonne=500,
    )
    assert forecast.forecast_points_json[0]["price_usd_per_tonne"] == 503.2

    with pytest.raises(ValueError):
        WorldCommodityForecast(
            commodity_slug="urea",
            generated_at=datetime.now(UTC),
            horizon_days=1,
            forecast_points_json=[{"date": "2026-05-27", "price_usd_per_tonne": -1}],
            model_kind="test",
            base_price_usd_per_tonne=500,
        )


def test_leaf_analysis_relationship_preserves_child_rows_on_session_delete():
    relationship = RecommendationSession.__mapper__.relationships["leaf_analyses"]

    assert "delete-orphan" not in relationship.cascade
    assert relationship.passive_deletes is True
