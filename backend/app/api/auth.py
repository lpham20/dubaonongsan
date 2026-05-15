from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db import get_db
from app.models import AppUser, WatchlistItem
from app.schemas import AuthCredentials, AuthRegisterCredentials, AuthTokenOut, AuthUserOut, WatchlistItemIn, WatchlistItemOut
from app.services.auth import (
    create_access_token,
    current_user,
    hash_password,
    password_needs_rehash,
    verify_password,
)


settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["auth"])


def user_out(user: AppUser) -> AuthUserOut:
    return AuthUserOut(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        is_admin=bool(user.is_admin),
    )


def auth_response(user: AppUser) -> AuthTokenOut:
    return AuthTokenOut(access_token=create_access_token(user), user=user_out(user))


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
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)
    return auth_response(user)


@router.post("/auth/login", response_model=AuthTokenOut)
@limiter.limit("10/minute")
def login(request: Request, payload: AuthCredentials, db: Session = Depends(get_db)) -> AuthTokenOut:
    email = payload.email.strip().lower()
    user = db.scalar(select(AppUser).where(AppUser.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        db.commit()
        db.refresh(user)
    return auth_response(user)


@router.get("/auth/me", response_model=AuthUserOut)
def me(user: AppUser = Depends(current_user)) -> AuthUserOut:
    return user_out(user)


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
