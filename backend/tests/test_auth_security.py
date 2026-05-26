import os
from datetime import UTC, datetime, timedelta

os.environ["MARKETAI_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["MARKETAI_START_SCHEDULER_IN_API"] = "false"

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.client_ip import get_client_ip
from app.db import SessionLocal
from app.main import app
from app.models import AppUser, AuthRefreshToken
from app.services import auth as auth_service


def test_register_uses_bcrypt_and_returns_jwt(test_password):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "secure@example.com", "password": test_password, "display_name": "Người dùng"},
        )
        assert response.status_code == 201
        token = response.json()["access_token"]
        assert token.count(".") == 2
        assert response.json()["refresh_token"]

        with SessionLocal() as db:
            user = db.scalar(select(AppUser).where(AppUser.email == "secure@example.com"))
            assert user is not None
            assert user.password_hash.startswith(("$2a$", "$2b$", "$2y$"))
            assert test_password not in user.password_hash


def test_refresh_token_rotates_and_rejects_reuse(test_password):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": test_password, "display_name": "Refresh"},
        )
        assert response.status_code == 201
        first_refresh = response.json()["refresh_token"]

        rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
        assert rotated.status_code == 200
        assert rotated.json()["access_token"].count(".") == 2
        assert rotated.json()["refresh_token"] != first_refresh

        reused = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
        assert reused.status_code == 401

        with SessionLocal() as db:
            rows = db.scalars(select(AuthRefreshToken).where(AuthRefreshToken.user_id == rotated.json()["user"]["user_id"])).all()
            assert len(rows) == 2
            assert sum(row.revoked_at is None for row in rows) == 1


def test_logout_revokes_refresh_token(test_password):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "logout-refresh@example.com", "password": test_password, "display_name": "Logout"},
        )
        assert response.status_code == 201
        payload = response.json()

        logout = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {payload['access_token']}"},
            json={"refresh_token": payload["refresh_token"]},
        )
        assert logout.status_code == 204

        refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
        assert refresh.status_code == 401


def test_logout_can_revoke_refresh_token_without_access_token(test_password):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "logout-refresh-only@example.com", "password": test_password, "display_name": "Logout Refresh Only"},
        )
        assert response.status_code == 201
        refresh_token = response.json()["refresh_token"]

        logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert logout.status_code == 204

        refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh.status_code == 401


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


def test_decode_accepts_previous_jwt_secret_during_rotation(monkeypatch):
    class Settings:
        auth_token_secret = "current-secret-" + ("x" * 48)
        auth_previous_token_secrets = "previous-secret-" + ("y" * 48)

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "42",
            "email": "rotating@example.com",
            "is_admin": False,
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "iss": auth_service.JWT_ISSUER,
            "aud": auth_service.JWT_AUDIENCE,
            "jti": "rotation-test",
        },
        "previous-secret-" + ("y" * 48),
        algorithm=auth_service.JWT_ALGORITHM,
    )

    monkeypatch.setattr(auth_service, "get_settings", lambda: Settings())

    payload = auth_service.decode_access_token(token, verify_revoked=False)

    assert payload["sub"] == "42"
