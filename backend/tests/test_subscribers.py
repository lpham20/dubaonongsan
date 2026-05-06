import os

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

from fastapi.testclient import TestClient

from app.main import app


def test_newsletter_subscription_validates_and_upserts():
    with TestClient(app) as client:
        invalid = client.post("/api/v1/content/subscribers", json={"email": "sai-dinh-dang"})
        assert invalid.status_code == 422

        created = client.post("/api/v1/content/subscribers", json={"email": "BaCon@Example.com"})
        assert created.status_code == 201
        assert created.json()["email"] == "bacon@example.com"

        duplicated = client.post("/api/v1/content/subscribers", json={"email": "bacon@example.com"})
        assert duplicated.status_code == 200
        assert duplicated.json()["subscriber_id"] == created.json()["subscriber_id"]
