from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.models import AppUser, RevokedToken


bearer_scheme = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "marketai"


def _legacy_hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))

    # Backward compatibility for local accounts created before bcrypt.
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False
    candidate = _legacy_hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected)


def password_needs_rehash(stored_hash: str) -> bool:
    return not stored_hash.startswith(("$2a$", "$2b$", "$2y$"))


def create_access_token(user: AppUser) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.user_id),
        "email": user.email,
        "is_admin": bool(user.is_admin),
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_token_minutes),
        "iss": JWT_ISSUER,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.auth_token_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, db: Session | None = None, verify_revoked: bool = True) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_token_secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token không hợp lệ") from exc
    if db is not None and verify_revoked:
        jti = payload.get("jti")
        if jti and db.get(RevokedToken, str(jti)) is not None:
            raise HTTPException(status_code=401, detail="Token da duoc dang xuat")
    return payload


def revoke_access_token(db: Session, token: str, user: AppUser) -> None:
    payload = decode_access_token(token, db=db, verify_revoked=False)
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or exp is None:
        return
    db.add(
        RevokedToken(
            jti=str(jti),
            user_id=user.user_id,
            revoked_at=datetime.now(UTC),
            expires_at=datetime.fromtimestamp(int(exp), tz=UTC),
        )
    )
    db.commit()


def cleanup_expired_revoked_tokens(db: Session) -> int:
    result = db.execute(delete(RevokedToken).where(RevokedToken.expires_at <= datetime.now(UTC)))
    db.commit()
    return int(result.rowcount or 0)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AppUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Cần đăng nhập")
    payload = decode_access_token(credentials.credentials, db=db)
    user = db.get(AppUser, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")
    return user


def require_admin(user: AppUser = Depends(current_user)) -> AppUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên mới có quyền này")
    return user
