from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.client_ip import get_client_ip
from app.core.config import get_settings
from app.db import get_db
from app.models import AppUser, AuthRefreshToken, RevokedToken


bearer_scheme = HTTPBearer(auto_error=False)
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "marketai"
JWT_AUDIENCE = "marketai-web"
INVALID_TOKEN_DETAIL = "Token không hợp lệ"
REVOCATION_CACHE_MAX_ITEMS = 4096
REVOCATION_CACHE_HIT_TTL_SECONDS = 10 * 60
REVOCATION_CACHE_MISS_TTL_SECONDS = 15
_REVOCATION_CACHE: dict[str, tuple[bool, datetime]] = {}
_REVOCATION_CACHE_LOCK = threading.Lock()


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
        "aud": JWT_AUDIENCE,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.auth_token_secret, algorithm=JWT_ALGORITHM)


def _candidate_token_secrets(settings) -> list[str]:
    previous_secrets = [
        secret.strip()
        for secret in str(getattr(settings, "auth_previous_token_secrets", "")).split(",")
        if secret.strip()
    ]
    return list(dict.fromkeys([settings.auth_token_secret, *previous_secrets]))


def _decode_with_secret(token: str, secret: str) -> dict:
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
    except jwt.MissingRequiredClaimError as exc:
        if str(getattr(exc, "claim", "")) != "aud":
            raise
        return jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"verify_aud": False},
        )


def decode_access_token(token: str, db: Session | None = None, verify_revoked: bool = True) -> dict:
    settings = get_settings()
    last_error: jwt.PyJWTError | None = None
    for secret in _candidate_token_secrets(settings):
        try:
            payload = _decode_with_secret(token, secret)
            break
        except jwt.PyJWTError as exc:
            last_error = exc
    else:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL) from last_error
    if db is not None and verify_revoked:
        jti = payload.get("jti")
        if jti and _is_access_token_revoked(db, str(jti)):
            raise HTTPException(status_code=401, detail="Token đã được đăng xuất")
    return payload


def revoke_access_token(db: Session, token: str, user: AppUser) -> None:
    payload = decode_access_token(token, db=db, verify_revoked=False)
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or exp is None:
        return
    jti = str(jti)
    if db.get(RevokedToken, jti) is not None:
        _cache_revocation(jti, True, REVOCATION_CACHE_HIT_TTL_SECONDS)
        return
    db.add(
        RevokedToken(
            jti=jti,
            user_id=user.user_id,
            revoked_at=datetime.now(UTC),
            expires_at=datetime.fromtimestamp(int(exp), tz=UTC),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    _cache_revocation(jti, True, REVOCATION_CACHE_HIT_TTL_SECONDS)


def cleanup_expired_revoked_tokens(db: Session) -> int:
    result = db.execute(delete(RevokedToken).where(RevokedToken.expires_at <= datetime.now(UTC)))
    db.commit()
    return int(result.rowcount or 0)


def create_refresh_token(
    db: Session,
    user: AppUser,
    *,
    request: Request | None = None,
    family_id: str | None = None,
) -> tuple[str, AuthRefreshToken]:
    settings = get_settings()
    now = datetime.now(UTC)
    raw_token = secrets.token_urlsafe(48)
    row = AuthRefreshToken(
        user_id=user.user_id,
        token_hash=_hash_refresh_token(raw_token),
        family_id=family_id or secrets.token_urlsafe(16),
        issued_at=now,
        expires_at=now + timedelta(days=max(1, settings.auth_refresh_token_days)),
        user_agent=(request.headers.get("user-agent", "")[:500] if request is not None else None),
        ip_address=(get_client_ip(request)[:64] if request is not None else None),
    )
    db.add(row)
    db.flush()
    return raw_token, row


def rotate_refresh_token(db: Session, refresh_token: str, *, request: Request | None = None) -> tuple[AppUser, str, AuthRefreshToken]:
    now = datetime.now(UTC)
    token_hash = _hash_refresh_token(refresh_token)
    row = db.scalar(select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_hash).with_for_update())
    if row is None or row.revoked_at is not None or _as_aware(row.expires_at) <= now:
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
    user = db.get(AppUser, row.user_id)
    if user is None:
        row.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail=INVALID_TOKEN_DETAIL)
    row.revoked_at = now
    raw_token, new_row = create_refresh_token(db, user, request=request, family_id=row.family_id)
    row.replaced_by_token_id = new_row.token_id
    db.add(row)
    db.commit()
    db.refresh(user)
    db.refresh(new_row)
    return user, raw_token, new_row


def revoke_refresh_token(db: Session, refresh_token: str, *, user: AppUser | None = None) -> bool:
    row = db.scalar(select(AuthRefreshToken).where(AuthRefreshToken.token_hash == _hash_refresh_token(refresh_token)))
    if row is None:
        return False
    if user is not None and row.user_id != user.user_id:
        return False
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        db.add(row)
        db.commit()
    return True


def cleanup_expired_refresh_tokens(db: Session) -> int:
    result = db.execute(delete(AuthRefreshToken).where(AuthRefreshToken.expires_at <= datetime.now(UTC)))
    db.commit()
    return int(result.rowcount or 0)


def revoke_user_refresh_tokens(db: Session, user: AppUser) -> int:
    result = db.execute(
        update(AuthRefreshToken)
        .where(AuthRefreshToken.user_id == user.user_id)
        .where(AuthRefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()
    return int(result.rowcount or 0)


def _hash_refresh_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_access_token_revoked(db: Session, jti: str) -> bool:
    cached = _get_cached_revocation(jti)
    if cached is not None:
        return cached
    revoked = db.get(RevokedToken, jti) is not None
    _cache_revocation(
        jti,
        revoked,
        REVOCATION_CACHE_HIT_TTL_SECONDS if revoked else REVOCATION_CACHE_MISS_TTL_SECONDS,
    )
    return revoked


def _get_cached_revocation(jti: str) -> bool | None:
    with _REVOCATION_CACHE_LOCK:
        cached = _REVOCATION_CACHE.get(jti)
        if cached is None:
            return None
        value, expires_at = cached
        if datetime.now(UTC) >= expires_at:
            _REVOCATION_CACHE.pop(jti, None)
            return None
        return value


def _cache_revocation(jti: str, value: bool, ttl_seconds: int) -> None:
    with _REVOCATION_CACHE_LOCK:
        if len(_REVOCATION_CACHE) >= REVOCATION_CACHE_MAX_ITEMS:
            oldest_key = min(_REVOCATION_CACHE, key=lambda key: _REVOCATION_CACHE[key][1])
            _REVOCATION_CACHE.pop(oldest_key, None)
        _REVOCATION_CACHE[jti] = (value, datetime.now(UTC) + timedelta(seconds=ttl_seconds))


def _as_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


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
