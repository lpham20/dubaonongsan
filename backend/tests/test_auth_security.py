import os

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import AppUser
from app.core.client_ip import get_client_ip


def test_register_uses_bcrypt_and_returns_jwt(test_password):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "secure@example.com", "password": test_password, "display_name": "Người dùng"},
        )
        assert response.status_code == 201
        token = response.json()["access_token"]
        assert token.count(".") == 2

        with SessionLocal() as db:
            user = db.scalar(select(AppUser).where(AppUser.email == "secure@example.com"))
            assert user is not None
            assert user.password_hash.startswith(("$2a$", "$2b$", "$2y$"))
            assert test_password not in user.password_hash


def test_login_rejects_bad_email_format(test_password):
    with TestClient(app) as client:
        response = client.post("/api/v1/auth/login", json={"email": "bad-email", "password": test_password})
        assert response.status_code == 422


def test_client_ip_rejects_multi_hop_spoofed_forwarded_for():
    class Headers(dict):
        def get(self, key, default=None):
            return super().get(key.lower(), default)

    class Request:
        client = type("Client", (), {"host": "172.18.0.5"})()
        headers = Headers({"x-forwarded-for": "1.2.3.4, 5.6.7.8"})

    assert get_client_ip(Request()) == "172.18.0.5"
