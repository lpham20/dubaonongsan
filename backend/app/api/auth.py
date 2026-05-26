from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db import get_db
from app.models import AppUser, WatchlistItem
from app.schemas import (
    AuthCredentials,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthRegisterCredentials,
    AuthTokenOut,
    AuthUserOut,
    WatchlistItemIn,
    WatchlistItemOut,
)
from app.services.auth import (
    bearer_scheme,
    create_access_token,
    create_refresh_token,
    current_user,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    revoke_refresh_token,
    revoke_access_token,
    rotate_refresh_token,
    verify_password,
)


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["auth"])
DUMMY_BCRYPT_HASH = "$2b$12$nP8tU4ECiTAA0st3I4n8kOu5.Pwbjyf4On1.hKHmtxkOjD/o/uZiC"
MAX_WATCHLIST_ITEMS_PER_USER = 50


def user_out(user: AppUser) -> AuthUserOut:
    return AuthUserOut(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        is_admin=bool(user.is_admin),
    )


def auth_response(user: AppUser, db: Session, request: Request) -> AuthTokenOut:
    refresh_token, refresh_row = create_refresh_token(db, user, request=request)
    db.commit()
    db.refresh(refresh_row)
    return AuthTokenOut(
        access_token=create_access_token(user),
        refresh_token=refresh_token,
        refresh_expires_at=refresh_row.expires_at,
        user=user_out(user),
    )


def _as_aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.post("/auth/register", response_model=AuthTokenOut, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, payload: AuthRegisterCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    email = payload.email.strip().lower()
    user = AppUser(
        email=email,
        display_name=payload.display_name or email.split("@", 1)[0],
        password_hash=hash_password(payload.password),
        created_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email đã tồn tại") from exc
    db.refresh(user)
    return auth_response(user, db, request)


@router.post("/auth/login", response_model=AuthTokenOut)
@limiter.limit("10/minute")
def login(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    email = payload.email.strip().lower()
    user = db.scalar(select(AppUser).where(AppUser.email == email))
    now = datetime.now(UTC)
    password_ok = verify_password(payload.password, user.password_hash if user is not None else DUMMY_BCRYPT_HASH)
    if user and user.locked_until and _as_aware_utc(user.locked_until) > now:
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if user is None or not password_ok:
        if user is not None:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
                user.failed_login_attempts = 0
            db.commit()
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    user.failed_login_attempts = 0
    user.locked_until = None
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)
    db.commit()
    db.refresh(user)
    return auth_response(user, db, request)


@router.post("/auth/refresh", response_model=AuthTokenOut)
@limiter.limit("20/minute")
def refresh_token(request: Request, payload: AuthRefreshRequest, db: Session = Depends(get_db)) -> AuthTokenOut:
    user, raw_refresh_token, refresh_row = rotate_refresh_token(db, payload.refresh_token, request=request)
    return AuthTokenOut(
        access_token=create_access_token(user),
        refresh_token=raw_refresh_token,
        refresh_expires_at=refresh_row.expires_at,
        user=user_out(user),
    )


@router.get("/auth/me", response_model=AuthUserOut)
def me(user: AppUser = Depends(current_user)) -> AuthUserOut:
    return user_out(user)


@router.post("/auth/logout", status_code=204)
def logout(
    payload: AuthLogoutRequest | None = Body(default=None),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Response:
    user: AppUser | None = None
    if credentials is not None:
        try:
            token_payload = decode_access_token(credentials.credentials, db=db, verify_revoked=False)
            user = db.get(AppUser, int(token_payload["sub"]))
            if user is not None:
                revoke_access_token(db, credentials.credentials, user)
        except (HTTPException, KeyError, TypeError, ValueError):
            user = None
    if payload and payload.refresh_token:
        revoke_refresh_token(db, payload.refresh_token, user=user)
    return Response(status_code=204)


@router.get("/watchlist", response_model=list[WatchlistItemOut])
def get_watchlist(
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[WatchlistItem]:
    return db.scalars(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user.user_id)
        .order_by(desc(WatchlistItem.created_at))
    ).all()


@router.post("/watchlist", response_model=WatchlistItemOut, status_code=201)
def save_watchlist_item(
    payload: WatchlistItemIn,
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> WatchlistItem:
    existing_count = db.scalar(select(func.count()).select_from(WatchlistItem).where(WatchlistItem.user_id == user.user_id)) or 0
    existing_item = db.scalar(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == user.user_id)
        .where(WatchlistItem.crop_type == payload.crop_type)
        .where(WatchlistItem.region_id == payload.region_id)
        .where(WatchlistItem.variety_id == payload.variety_id)
    )
    if existing_item is None and existing_count >= MAX_WATCHLIST_ITEMS_PER_USER:
        raise HTTPException(status_code=400, detail="Danh sách ghim đã đạt giới hạn 50 mục.")
    item = WatchlistItem(
        user_id=user.user_id,
        crop_type=payload.crop_type,
        region_id=payload.region_id,
        variety_id=payload.variety_id,
        label=payload.label,
        created_at=datetime.now(UTC),
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        item = db.scalar(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user.user_id)
            .where(WatchlistItem.crop_type == payload.crop_type)
            .where(WatchlistItem.region_id == payload.region_id)
            .where(WatchlistItem.variety_id == payload.variety_id)
        )
        if item is None:
            raise
        item.label = payload.label
        db.add(item)
        db.commit()
    db.refresh(item)
    return item


@router.delete("/watchlist/{item_id}", status_code=204)
def delete_watchlist_item(
    item_id: int,
    user: AppUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    item = db.get(WatchlistItem, item_id)
    if item is None or item.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy mục ghim")
    db.delete(item)
    db.commit()
    return Response(status_code=204)
