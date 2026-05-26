from copy import deepcopy
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
from statistics import mean

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

from fastapi.testclient import TestClient
import pytest

from app.db import SessionLocal
from app.main import app
from app.models import AppUser, RevokedToken
from app.services.auth import create_access_token, hash_password


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_user_token(email: str, password: str = "StrongPass123", *, is_admin: bool = False) -> tuple[str, int]:
    with SessionLocal() as db:
        user = AppUser(
            email=email,
            display_name=email.split("@", 1)[0],
            password_hash=hash_password(password),
            created_at=datetime.now(UTC),
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_access_token(user), user.user_id


FERTILIZER_RECOMMENDATION_PAYLOAD = {
    "crop": "robusta_coffee",
    "growth_stage": "mature_kinh_doanh",
    "yield_target_t_ha": 3.5,
    "tree_density_per_ha": 1100,
    "soil": {
        "texture": "basaltic_red",
        "ph_kcl": 4.3,
        "organic_carbon_pct": 2.8,
        "total_n_pct": 0.18,
        "available_p_method": "bray_ii",
        "available_p_mg_per_100g": 4.5,
        "exchangeable_k_method": "nh4oac",
        "exchangeable_k2o_mg_per_100g": 12,
        "cec_cmolc_per_kg": 8,
        "sample_depth_cm": 30,
        "sample_date": "2026-05-21",
    },
    "location": {"province": "Dak Lak"},
    "climate": {"annual_rainfall_mm": 1900, "irrigation_available": True},
    "field": {"slope_pct": 5, "years_under_current_crop": 10},
    "preferences": {"language": "vi", "include_product_mix": True},
}


def test_historical_prices_returns_seeded_points(client):
    response = client.get("/api/v1/analytics/historical-prices?region_id=1&variety=1&limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 5
    assert payload[0]["max_price_vnd"] > 0


def test_regions_metadata_only_returns_production_locations(client):
    response = client.get("/api/v1/metadata/regions")
    assert response.status_code == 200
    payload = response.json()
    labels = {row["province"] or row["region_name"] for row in payload}
    assert "Thủ Đức" not in labels
    assert "Bình Điền" not in labels
    assert "Thị trường Việt Nam" not in labels
    assert "Đồng Tháp" in labels
    assert "Tiền Giang" not in labels
    assert "Đắk Lắk" in labels


def test_forecast_returns_30_days(client):
    response = client.get("/api/v1/analytics/forecast-30-days?region_id=1&variety=1")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 30
    assert payload[0]["forecast_price_vnd"] > 0
    assert payload[0]["model_kind"] == "baseline-statistical"


def test_input_price_endpoints_return_fertilizer_data(client):
    products = client.get("/api/v1/input-prices/products?category=fertilizer")
    assert products.status_code == 200
    product_payload = products.json()
    assert any(item["slug"] == "ure" for item in product_payload)

    latest = client.get("/api/v1/input-prices/latest?category=fertilizer&product_slug=ure&province=Đắk Lắk")
    assert latest.status_code == 200
    latest_payload = latest.json()
    assert latest_payload
    assert latest_payload[0]["product_slug"] == "ure"
    assert latest_payload[0]["package_price_vnd"] > 0
    assert latest_payload[0]["normalized_price_vnd"] > 0

    history = client.get("/api/v1/input-prices/history?product_slug=ure&province=Đắk Lắk&months=12")
    assert history.status_code == 200
    assert len(history.json()) >= 12

    forecast = client.get("/api/v1/input-prices/forecast?product_slug=ure&province=Đắk Lắk&days=30")
    assert forecast.status_code == 200
    forecast_payload = forecast.json()
    assert forecast_payload["model_kind"] == "input-price-seasonal-v3"
    assert len(forecast_payload["points"]) == 30
    values = [row["forecast_price_vnd"] for row in forecast_payload["points"]]
    assert max(values) - min(values) >= 0.01 * mean(values)
    day_1_band = forecast_payload["points"][0]["confidence_high_vnd"] - forecast_payload["points"][0]["confidence_low_vnd"]
    day_30_band = forecast_payload["points"][-1]["confidence_high_vnd"] - forecast_payload["points"][-1]["confidence_low_vnd"]
    assert day_30_band > day_1_band

    health = client.get("/api/v1/platform/input-prices/health")
    assert health.status_code == 200
    assert health.json()["category"] == "fertilizer"


def test_input_price_public_scrapers_parse_verified_shapes():
    from app.ingestion.input_price_registry import INPUT_PRICE_SCRAPERS
    from app.ingestion.sources.fertilizer_public_sources import (
        CoffeeMarketFertilizerPriceScraper,
        SFarmOrganicFertilizerPriceScraper,
        TheFinancesFertilizerPriceScraper,
        VinacamFertilizerPriceScraper,
    )

    assert {"vinacam_fertilizer", "thefinances_fertilizer", "sfarm_organic_fertilizer", "coffee_market_fertilizer"} <= set(
        INPUT_PRICE_SCRAPERS
    )

    vinacam = VinacamFertilizerPriceScraper().parse_html(
        """
        <p>Giá phân bón cập nhật ngày: 06/05/2026</p>
        <table>
          <tr><th>#</th><th>Tên Phân Bón</th><th>Thị Trường</th><th>Ghi chú</th></tr>
          <tr><th>HCM</th><th>HN</th><th>Quy Nhơn</th></tr>
          <tr><td></td><td>Phân Urea Hà Bắc</td><td>18.000</td><td>-</td><td>-</td><td></td></tr>
        </table>
        """
    )
    assert len(vinacam.observations) == 1
    assert vinacam.observations[0].product_slug == "ure"
    assert vinacam.observations[0].package_price_vnd == 900_000

    finances = TheFinancesFertilizerPriceScraper().parse_html(
        """
        <h1>Giá phân bón hôm nay cập nhật 22/05/2026</h1>
        <table>
          <tr><td>An Giang</td><td>DAP Trung Quốc</td><td>22,000</td><td>đ/kg</td><td>Đại lý cấp I</td></tr>
          <tr><td>Cà Mau</td><td>Phân lân</td><td>2,450</td><td>đ/kg</td><td>Bán lẻ</td></tr>
        </table>
        """
    )
    assert {row.province for row in finances.observations} == {"An Giang", "Cà Mau"}
    assert any(row.product_slug == "dap" and row.package_price_vnd == 1_100_000 for row in finances.observations)

    sfarm = SFarmOrganicFertilizerPriceScraper().parse_html(
        """
        <p>Bảng giá được cập nhật vào 21/01/2026.</p>
        <table>
          <tr><th>Sản phẩm</th><th>Quy cách</th><th>Giá tham khảo</th></tr>
          <tr><td>Phân bò SFARM</td><td>25 kg</td><td>~215.000đ / túi</td></tr>
        </table>
        """
    )
    assert sfarm.observations[0].product_slug == "phan-bo-u-hoai-sfarm"
    assert sfarm.observations[0].package_size_kg == 25
    assert sfarm.observations[0].package_price_vnd == 215_000

    coffee_market = CoffeeMarketFertilizerPriceScraper().parse_html(
        """
        <main>
          <p>Cập nhật lần cuối: 25/1/2026</p>
          <p>Phân URÊ</p><p>Cà Mau</p><p>610.000</p><p>-</p><p>650.000</p><p>đ/bao</p>
          <p>Phân NPK 16-16-8</p><p>Đầu Trâu</p><p>670.000</p><p>-</p><p>750.000</p><p>đ/bao</p>
        </main>
        """,
        province="Đắk Lắk",
    )
    assert len(coffee_market.observations) == 2
    assert {row.province for row in coffee_market.observations} == {"Đắk Lắk"}


def test_input_price_store_keeps_package_size_variants(client):
    from sqlalchemy import select

    from app.ingestion.input_price_records import InputPriceObservation, InputPriceScrapeResult
    from app.ingestion.input_price_service import InputPriceIngestionService
    from app.models import AgriInputPriceObservation, AgriInputProduct
    from app.services.input_prices import InputPriceService

    observed_at = datetime(2026, 1, 21, tzinfo=UTC)
    result = InputPriceScrapeResult(
        source="test-sfarm",
        source_url="https://example.test/sfarm",
        observations=[
            InputPriceObservation(
                observed_at=observed_at,
                product_slug="test-sfarm-organic",
                product_name="Test SFARM organic",
                product_type="Phân hữu cơ",
                nutrient_profile="Hữu cơ",
                province="TP.HCM",
                region_name="Đông Nam Bộ",
                brand="SFARM",
                seller_name="SFARM",
                source="test-sfarm",
                source_url="https://example.test/sfarm",
                package_price_vnd=26_000,
                package_size_kg=2,
            ),
            InputPriceObservation(
                observed_at=observed_at,
                product_slug="test-sfarm-organic",
                product_name="Test SFARM organic",
                product_type="Phân hữu cơ",
                nutrient_profile="Hữu cơ",
                province="TP.HCM",
                region_name="Đông Nam Bộ",
                brand="SFARM",
                seller_name="SFARM",
                source="test-sfarm",
                source_url="https://example.test/sfarm",
                package_price_vnd=215_000,
                package_size_kg=25,
            ),
        ],
    )
    with SessionLocal() as db:
        service = InputPriceIngestionService(db)
        inserted, updated = service.store(result)
        assert inserted == 2
        assert updated == 0
        rows = db.scalars(
            select(AgriInputPriceObservation)
            .join(AgriInputProduct)
            .where(AgriInputProduct.slug == "test-sfarm-organic")
            .order_by(AgriInputPriceObservation.package_size_kg)
        ).all()
        assert [float(row.package_size_kg) for row in rows] == [2, 25]

        latest = InputPriceService(db).latest_prices(
            product_slug="test-sfarm-organic",
            province="TP.HCM",
        )
        assert sorted(row["package_size_kg"] for row in latest) == [2, 25]


def test_world_fertilizer_forecast_returns_daily_percent_changes(client):
    from app.models import WorldCommodityPrice

    with SessionLocal() as db:
        start = datetime.now(UTC) - timedelta(days=44)
        for index in range(45):
            db.add(
                WorldCommodityPrice(
                    commodity_slug="urea",
                    quote_type="Trading Economics Urea benchmark",
                    source="tradingeconomics_urea_daily",
                    source_url="https://example.test/urea-daily",
                    observed_at=start + timedelta(days=index),
                    price_usd_per_tonne=320 + index * 7,
                    currency="USD",
                    confidence_score=0.95,
                    raw_json={"symbol": "UREA:COM"},
                    created_at=datetime.now(UTC),
                )
            )
            db.add(
                WorldCommodityPrice(
                    commodity_slug="urea",
                    quote_type="CME Urea Granular FOB Middle East futures continuous",
                    source="yahoo_urea_futures_daily",
                    source_url="https://example.test/yahoo-urea",
                    observed_at=start + timedelta(days=index),
                    price_usd_per_tonne=900 + index,
                    currency="USD",
                    confidence_score=0.75,
                    raw_json={"symbol": "UME=F"},
                    created_at=datetime.now(UTC),
                )
            )
        db.add(
            WorldCommodityPrice(
                commodity_slug="urea",
                quote_type="FOB Middle East",
                source="worldbank_pinksheet",
                source_url="https://example.test/worldbank.xlsx",
                observed_at=start + timedelta(days=44),
                price_usd_per_tonne=999,
                currency="USD",
                confidence_score=0.95,
                raw_json={"series_code": "UREA_TEST"},
                created_at=datetime.now(UTC),
            )
        )
        db.commit()

    commodities = client.get("/api/v1/advisory/world-fertilizer/commodities")
    assert commodities.status_code == 200
    assert {item["commodity_slug"] for item in commodities.json()} >= {"urea", "dap", "kali_mop"}

    forecast = client.get("/api/v1/advisory/world-fertilizer/forecast?commodity=urea&horizon_days=30")
    assert forecast.status_code == 200
    payload = forecast.json()
    assert payload["commodity_slug"] == "urea"
    assert payload["model_kind"] == "world-fertilizer-anchor-ewma-ar1-v2"
    assert payload["source_mode"] == "daily_signal"
    assert payload["data_quality"]["history_points"] >= 14
    assert payload["base_price_usd_per_tonne"] == 628
    assert payload["quote_type"] == "Trading Economics Urea benchmark"
    assert len(payload["forecast_daily"]) == 30
    assert len(payload["forecast_weekly"]) >= 4
    first = payload["forecast_daily"][0]
    assert first["price_usd_per_tonne"] > 0
    assert "daily_pct_change" in first
    assert "cumulative_pct_from_today" in first

    invalid = client.get("/api/v1/advisory/world-fertilizer/forecast?commodity=invalid")
    assert invalid.status_code == 400


def test_arbitrage_excludes_aggregate_and_wholesale_regions(client):
    from sqlalchemy import select

    from app.models import DailyMarketPrice, DurianVariety, ProductionRegion

    with SessionLocal() as db:
        variety = db.scalar(select(DurianVariety).where(DurianVariety.crop_type == "sau_rieng"))
        aggregate = db.scalar(select(ProductionRegion).where(ProductionRegion.region_name == "Thị trường Việt Nam"))
        if aggregate is None:
            aggregate = ProductionRegion(region_name="Thị trường Việt Nam", province=None, export_code=None, risk_level_index=0)
            db.add(aggregate)
            db.flush()
        allowed = {
            row.province: row
            for row in db.scalars(select(ProductionRegion).where(ProductionRegion.province.in_(["Cần Thơ", "Đồng Nai"]))).all()
        }
        assert variety is not None and {"Cần Thơ", "Đồng Nai"} <= set(allowed)
        prices = [(aggregate, 30_000), (allowed["Cần Thơ"], 55_000), (allowed["Đồng Nai"], 95_000)]
        observed_at = datetime.now(UTC) + timedelta(minutes=2)
        for region, price in prices:
            db.add(
                DailyMarketPrice(
                    record_timestamp=observed_at,
                    variety_id=variety.variety_id,
                    crop_type="sau_rieng",
                    quality_grade="pytest",
                    region_id=region.region_id,
                    exchange_source="pytest-arbitrage",
                    min_price_vnd=price,
                    max_price_vnd=price,
                )
            )
        db.commit()

    token, _user_id = create_user_token("arbitrage@example.com")
    response = client.get(
        "/api/v1/advisory/arbitrage?crop_type=sau_rieng&min_net_spread_pct=0&max_distance_km=3000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    labels = {item["from_region"] for item in response.json()["items"]} | {item["to_region"] for item in response.json()["items"]}
    assert "Thị trường Việt Nam" not in labels
    assert "Chợ đầu mối TP.HCM" not in labels
    assert labels <= {"Cần Thơ", "Vĩnh Long", "Đồng Tháp", "Đắk Lắk", "Lâm Đồng", "Đồng Nai", "Tây Ninh"}


def test_advisory_decision_tools_require_login(client):
    assert client.get("/api/v1/advisory/arbitrage").status_code == 401
    assert client.post(
        "/api/v1/advisory/selling-time",
        json={"crop": "sau_rieng", "quantity_kg": 1000},
    ).status_code == 401
    assert client.post(
        "/api/v1/advisory/cross-commodity",
        json={"region_id": 1, "area_hectares": 1},
    ).status_code == 401


def test_sensor_webhook_persists_payload(client):
    response = client.post(
        "/api/v1/sensors/maturity-telemetry",
        headers={"x-api-key": "marketai-iot-dev-key"},
        json={
            "device_id": "T-Abyss-001",
            "region_id": 1,
            "maturity_index": 8.2,
            "status": "Sẵn sàng thu hoạch",
            "timestamp": "2026-04-28T09:10:00Z",
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] > 0


def test_roi_calculate_and_save(client):
    token, _user_id = create_user_token("roi@example.com")
    response = client.post(
        "/api/v1/roi/calculate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop": "ca_phe",
            "crop_area_ha": 2,
            "expected_yield_t_ha": 3.5,
            "expected_sell_price_vnd_per_kg": 95000,
            "fertilizer_lines": [
                {"product_slug": "ure", "kg_per_ha": 300},
                {"product_slug": "kali-mop", "kg_per_ha": 200},
            ],
            "other_input_cost_vnd_per_ha": 5000000,
            "labor_cost_vnd_per_ha": 8000000,
            "save": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_id"]
    assert payload["fertilizer_cost_vnd_per_ha"] > 0
    assert payload["total_revenue_vnd"] > payload["fertilizer_cost_vnd_per_ha"]
    assert len(payload["scenarios"]) == 1
    assert len(payload["sensitivity"]["matrix"]) == 9


def test_advisory_roi_simple_mode(client):
    token, _user_id = create_user_token("advisory-roi@example.com")
    response = client.post(
        "/api/v1/advisory/roi/calculate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop": "sau_rieng",
            "crop_area_ha": 1.2,
            "expected_yield_t_ha": 16,
            "expected_sell_price_vnd_per_kg": 72000,
            "fertilizer_total_cost_vnd_per_ha": 38000000,
            "other_input_cost_vnd_per_ha": 12000000,
            "labor_cost_vnd_per_ha": 18000000,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["fertilizer_input_mode"] == "simple"
    assert payload["fertilizer_cost_vnd_per_ha"] == 38000000
    assert len(payload["scenarios"]) == 1
    assert payload["recommendations_vi"]


def test_roi_rejects_duplicate_fertilizer_slug(client):
    token, _user_id = create_user_token("roi-duplicate@example.com")
    response = client.post(
        "/api/v1/advisory/roi/calculate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "crop": "ca_phe",
            "crop_area_ha": 1,
            "expected_yield_t_ha": 3.2,
            "expected_sell_price_vnd_per_kg": 95000,
            "fertilizer_lines": [
                {"product_slug": "ure", "kg_per_ha": 120, "price_vnd_per_kg": 14500},
                {"product_slug": "ure", "kg_per_ha": 80, "price_vnd_per_kg": 14600},
            ],
            "other_input_cost_vnd_per_ha": 5000000,
            "labor_cost_vnd_per_ha": 8000000,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "DUPLICATE_FERTILIZER"


def test_lstm_artifact_meta_consistency():
    artifacts = Path(__file__).resolve().parents[1] / "ml_artifacts"
    for crop in ["sau_rieng", "ca_phe", "ho_tieu", "lua"]:
        meta = json.loads((artifacts / f"lstm_{crop}.meta.json").read_text(encoding="utf-8"))
        scaler = json.loads((artifacts / f"lstm_{crop}.scaler.json").read_text(encoding="utf-8"))
        assert meta.get("target_mode") == scaler.get("target_mode"), crop


def test_auth_and_watchlist_flow(client, test_password):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "farmer@example.com", "password": test_password, "display_name": "Farmer"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/watchlist",
        headers={"Authorization": f"Bearer {token}"},
        json={"crop_type": "sau_rieng", "region_id": 1, "variety_id": 1, "label": "Tiền Giang - Ri6"},
    )
    assert response.status_code == 201

    response = client.get("/api/v1/watchlist", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()[0]["label"] == "Tiền Giang - Ri6"


def test_fertilizer_recommendation_requires_login(client, test_password):
    response = client.post("/api/v1/fertilizer/recommend", json=FERTILIZER_RECOMMENDATION_PAYLOAD)
    assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "fertilizer@example.com", "password": test_password, "display_name": "Fertilizer User"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    response = client.post(
        "/api/v1/fertilizer/recommend",
        headers={"Authorization": f"Bearer {token}"},
        json=FERTILIZER_RECOMMENDATION_PAYLOAD,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "recommendation" in payload
    assert len(payload["session_id"]) == 36
    assert len(payload["session_code"]) == 8

    feedback = client.post(
        f"/api/v1/sessions/{payload['session_code']}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "actual_yield_t_ha": 3.8,
            "harvest_date": "2026-12-10",
            "fertilizer_followed_pct": 85,
            "rating": 4,
            "note": "Vườn làm theo phần lớn khuyến nghị.",
        },
    )
    assert feedback.status_code == 201
    assert feedback.json()["session_code"] == payload["session_code"]


def test_yield_feedback_requires_auth_and_owner(client):
    owner_token, _ = create_user_token("feedback-owner@example.com")
    other_token, _ = create_user_token("feedback-other@example.com")

    recommendation = client.post(
        "/api/v1/fertilizer/recommend",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=FERTILIZER_RECOMMENDATION_PAYLOAD,
    )
    assert recommendation.status_code == 200
    session_code = recommendation.json()["session_code"]

    payload = {
        "actual_yield_t_ha": 3.6,
        "harvest_date": "2026-12-15",
        "fertilizer_followed_pct": 90,
        "rating": 5,
        "contact_phone": "0912345678",
    }

    anonymous = client.post(f"/api/v1/sessions/{session_code}/feedback", json=payload)
    assert anonymous.status_code == 401

    other_user = client.post(
        f"/api/v1/sessions/{session_code}/feedback",
        headers={"Authorization": f"Bearer {other_token}"},
        json=payload,
    )
    assert other_user.status_code == 403

    wildcard = client.post(
        f"/api/v1/sessions/{session_code[:7]}_/feedback",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert wildcard.status_code == 404

    owner = client.post(
        f"/api/v1/sessions/{session_code}/feedback",
        headers={"Authorization": f"Bearer {owner_token}"},
        json=payload,
    )
    assert owner.status_code == 201


def test_login_lockout_after_5_failed_attempts(client):
    create_user_token("lockout@example.com", "CorrectPass123")
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "lockout@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "lockout@example.com", "password": "CorrectPass123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email hoặc mật khẩu không đúng"


def test_logout_revokes_token_and_cleanup_job(client):
    token, user_id = create_user_token("logout@example.com")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 204
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    admin_token, _ = create_user_token("cleanup-admin@example.com", is_admin=True)
    with SessionLocal() as db:
        db.add(
            RevokedToken(
                jti="expired-test-token",
                user_id=user_id,
                revoked_at=datetime.now(UTC) - timedelta(days=2),
                expires_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        db.commit()

    cleanup = client.post(
        "/api/v1/platform/jobs/revoked-token-cleanup",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cleanup.status_code == 200
    assert cleanup.json()["deleted"] >= 1


def test_fertilizer_tier1_agronomy_rules():
    from app.services.fertilizer_engine import recommend

    coffee = recommend(deepcopy(FERTILIZER_RECOMMENDATION_PAYLOAD))
    coffee_splits = coffee["recommendation"]["splits"]
    assert sum(item["n_pct"] for item in coffee_splits) == 100
    assert sum(item["p2o5_pct"] for item in coffee_splits) == 100
    assert sum(item["k2o_pct"] for item in coffee_splits) == 100
    post_harvest = coffee_splits[0]
    assert post_harvest["calendar_window"] == "Tháng 1-2"
    assert (post_harvest["n_pct"], post_harvest["p2o5_pct"], post_harvest["k2o_pct"]) == (15, 50, 15)
    assert coffee["confidence"]["calibration_tier"] == "high"
    assert coffee["confidence"]["badge_vi"] == "Đã hiệu chuẩn"

    durian = deepcopy(FERTILIZER_RECOMMENDATION_PAYLOAD)
    durian.update({"crop": "durian", "variety": "Ri6", "yield_target_t_ha": 25, "tree_density_per_ha": 150})
    durian["soil"]["texture"] = "basaltic_red"
    durian["soil"]["available_p_mg_per_kg"] = 18
    durian_result = recommend(durian)
    durian_total = durian_result["recommendation"]["annual_total"]
    assert durian_total["n_kg_ha"] <= 300
    assert durian_total["p2o5_kg_ha"] <= 200
    assert durian_total["k2o_kg_ha"] <= 250
    assert durian_result["confidence"]["calibration_tier"] == "low"
    assert durian_result["confidence"]["badge_vi"] == "Tham chiếu quốc tế"
    assert all("WASI 2025" not in item["title"] for item in durian_result["rationale"]["sources_cited"])

    pepper = deepcopy(FERTILIZER_RECOMMENDATION_PAYLOAD)
    pepper.update({"crop": "black_pepper", "yield_target_t_ha": 3, "tree_density_per_ha": 1600})
    pepper["soil"]["texture"] = "basaltic_red"
    pepper["soil"]["available_p_mg_per_100g"] = None
    pepper["soil"]["available_p_mg_per_kg"] = 110
    pepper_result = recommend(pepper)
    assert pepper_result["recommendation"]["annual_total"]["p2o5_kg_ha"] == 0
    assert any(warning["code"] == "PEPPER_P_EXCESS" for warning in pepper_result["warnings"])
    assert pepper_result["confidence"]["calibration_tier"] == "medium"

    fruit_fill = deepcopy(durian)
    fruit_fill["growth_stage"] = "fruit_fill"
    fruit_fill["preferences"] = {"language": "vi", "include_product_mix": True, "preferred_k_source": "kcl"}
    fruit_fill_result = recommend(fruit_fill)
    fruit_fill_products = fruit_fill_result["recommendation"]["product_mix_options"][0]["products"]
    assert any(product["sku"] == "phu_my_k2so4_50" for product in fruit_fill_products)
    assert any(warning["code"] == "DURIAN_NO_KCL_FRUIT_FILL" for warning in fruit_fill_result["warnings"])

    fruit_set = deepcopy(durian)
    fruit_set["growth_stage"] = "fruit_set"
    fruit_set["preferences"] = {"language": "vi", "include_product_mix": True, "preferred_k_source": "kcl"}
    fruit_set_result = recommend(fruit_set)
    fruit_set_products = fruit_set_result["recommendation"]["product_mix_options"][0]["products"]
    assert any(product["sku"] == "phu_my_kcl_60" for product in fruit_set_products)
    assert not any(warning["code"] == "DURIAN_NO_KCL_FRUIT_FILL" for warning in fruit_set_result["warnings"])


def test_public_api_requires_key(client):
    response = client.get("/api/v1/public/prices?region_id=1&variety_id=1&limit=2")
    assert response.status_code == 401

    response = client.get(
        "/api/v1/public/prices?region_id=1&variety_id=1&limit=2",
        headers={"x-api-key": "marketai-public-demo-key"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_admin_endpoints_reject_anonymous_and_non_admin_users(client, test_password):
    anonymous = client.post("/api/v1/ingestion/scrape-prices")
    assert anonymous.status_code == 401
    anonymous_runs = client.get("/api/v1/ingestion/scrape-runs")
    assert anonymous_runs.status_code == 401

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "viewer@example.com", "password": test_password, "display_name": "Viewer"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    protected_routes = [
        "/api/v1/content/news/scrape",
        "/api/v1/platform/jobs/scrape",
        "/api/v1/platform/jobs/data-quality",
        "/api/v1/platform/jobs/news",
        "/api/v1/platform/jobs/input-prices-backfill",
        "/api/v1/platform/jobs/world-fertilizer",
        "/api/v1/platform/jobs/retrain",
        "/api/v1/platform/jobs/yield-feedback-reminder",
        "/api/v1/platform/jobs/revoked-token-cleanup",
        "/api/v1/ingestion/backfill-model-ready",
        "/api/v1/ingestion/scrape-world-fertilizer",
    ]
    for route in protected_routes:
        response = client.post(route, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403

    response = client.get("/api/v1/ingestion/scrape-runs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_sensor_webhook_requires_iot_key(client):
    response = client.post(
        "/api/v1/sensors/maturity-telemetry",
        json={
            "device_id": "T-Abyss-002",
            "region_id": 1,
            "maturity_index": 7.4,
            "timestamp": "2026-04-28T09:10:00Z",
        },
    )
    assert response.status_code == 401


def test_image_proxy_blocks_private_or_untrusted_hosts(client):
    response = client.get("/api/v1/content/image-proxy?url=http://127.0.0.1/test.jpg")
    assert response.status_code == 403
    response = client.get("/api/v1/content/image-proxy?url=https://attacker.com/test.jpg")
    assert response.status_code == 403


def test_excel_and_pdf_exports(client):
    xlsx = client.get("/api/v1/analytics/export.xlsx?region_id=1&variety=1")
    pdf = client.get("/api/v1/analytics/export.pdf?region_id=1&variety=1")

    assert xlsx.status_code == 200
    assert xlsx.content.startswith(b"PK")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_content_portal_returns_news_and_guides(client):
    news = client.get("/api/v1/content/news")
    guides = client.get("/api/v1/content/guides?crop=sau_rieng")

    assert news.status_code == 200
    assert news.json()[0]["source_url"].startswith("https://")
    assert guides.status_code == 200
    assert any("sầu riêng" in item["title"].lower() for item in guides.json())


def test_sitemap_includes_static_seo_routes(client):
    response = client.get("/api/v1/sitemap.xml")
    assert response.status_code == 200
    body = response.text
    assert "https://dubaonongsan.com/khuyen-nghi-bon-phan" in body
    assert "https://dubaonongsan.com/khuyen-nghi-bon-phan/logic" in body
    assert "https://dubaonongsan.com/bao-cao-nang-suat" in body
    assert "https://dubaonongsan.com/roi-uoc-tinh" in body


def test_news_filter_rejects_offtopic_finance_and_electricity():
    from datetime import UTC, datetime

    from app.models import NewsArticle
    from app.services.content_portal import _is_keepable_news_article

    now = datetime.now(UTC)
    off_topic_rows = [
        NewsArticle(
            source_name="Báo Nông nghiệp và Môi trường",
            source_url="https://nongnghiepmoitruong.vn/quy-i-2026-mb-bao-lai-hon-9600-ty-dong-d809001.html",
            title="Quý I/2026: MB báo lãi hơn 9.600 tỷ đồng",
            summary="Ngân hàng ghi nhận lợi nhuận tăng trong quý I.",
            excerpt="Ngân hàng ghi nhận lợi nhuận tăng trong quý I.",
            category="Ảnh hưởng giá",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
        NewsArticle(
            source_name="Báo Nông nghiệp và Môi trường",
            source_url="https://nongnghiepmoitruong.vn/evn-dam-bao-cung-ung-dien-dip-nghi-le-30-4--1-5-d809053.html",
            title="EVN đảm bảo cung ứng điện dịp nghỉ lễ 30/4 - 1/5",
            summary="Ngành điện lên kế hoạch cung ứng điện cho kỳ nghỉ lễ.",
            excerpt="Ngành điện lên kế hoạch cung ứng điện cho kỳ nghỉ lễ.",
            category="Ảnh hưởng giá",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
    ]

    assert all(not _is_keepable_news_article(row) for row in off_topic_rows)


def test_news_filter_keeps_agricultural_market_news():
    from datetime import UTC, datetime

    from app.models import NewsArticle
    from app.services.content_portal import _is_keepable_news_article

    now = datetime.now(UTC)
    rows = [
        NewsArticle(
            source_name="Báo Nông nghiệp và Môi trường",
            source_url="https://nongnghiepmoitruong.vn/xuat-khau-ca-phe-viet-nam-tang-manh-d809101.html",
            title="Xuất khẩu cà phê Việt Nam tăng mạnh trong tháng 4",
            summary="Giá cà phê và nhu cầu nhập khẩu từ châu Âu tiếp tục nâng sức mua.",
            excerpt="Giá cà phê và nhu cầu nhập khẩu từ châu Âu tiếp tục nâng sức mua.",
            category="Xuất khẩu",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
        NewsArticle(
            source_name="Báo Công Thương",
            source_url="https://congthuong.vn/gia-phan-bon-va-vat-tu-nong-nghiep-can-duoc-theo-doi-809102.html",
            title="Giá phân bón và vật tư nông nghiệp cần được theo dõi sát",
            summary="Chi phí đầu vào thay đổi có thể ảnh hưởng đến kế hoạch mùa vụ.",
            excerpt="Chi phí đầu vào thay đổi có thể ảnh hưởng đến kế hoạch mùa vụ.",
            category="Phân bón - vật tư",
            image_url=None,
            published_at=now,
            scraped_at=now,
        ),
    ]

    assert all(_is_keepable_news_article(row) for row in rows)
