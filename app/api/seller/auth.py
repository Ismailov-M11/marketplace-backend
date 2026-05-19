from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select, update

from app.api.deps import DB, CurrentSellerUser
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.audit import RefreshToken
from app.models.seller import SellerUser
from app.schemas.auth import ChangePasswordRequest, LoginRequest, SellerUserOut, TokenResponse
from app.settings import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def seller_login(body: LoginRequest, request: Request, response: Response, db: DB):
    result = await db.execute(
        select(SellerUser).where(SellerUser.email == body.email, SellerUser.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")

    await db.execute(
        update(SellerUser).where(SellerUser.id == user.id).values(last_login_at=datetime.now(timezone.utc))
    )

    access_token = create_access_token({
        "sub": user.id, "type": "seller", "role": user.role, "seller_id": user.seller_id
    })
    raw_refresh, hashed_refresh = create_refresh_token()

    db.add(RefreshToken(
        user_type="seller",
        user_id=user.id,
        token_hash=hashed_refresh,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    ))

    response.set_cookie(
        "refresh_token", raw_refresh,
        httponly=True, samesite="lax", secure=not settings.is_development,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def seller_refresh(request: Request, response: Response, db: DB):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise UnauthorizedError("No refresh token")

    hashed = hash_token(raw)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hashed,
            RefreshToken.user_type == "seller",
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise UnauthorizedError("Invalid or expired refresh token")

    rt.revoked_at = datetime.now(timezone.utc)
    await db.flush()

    user_result = await db.execute(
        select(SellerUser).where(SellerUser.id == rt.user_id, SellerUser.is_active == True)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")

    access_token = create_access_token({
        "sub": user.id, "type": "seller", "role": user.role, "seller_id": user.seller_id
    })
    new_raw, new_hashed = create_refresh_token()

    db.add(RefreshToken(
        user_type="seller",
        user_id=user.id,
        token_hash=new_hashed,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))

    response.set_cookie(
        "refresh_token", new_raw,
        httponly=True, samesite="lax", secure=not settings.is_development,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return TokenResponse(access_token=access_token, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def seller_logout(request: Request, response: Response, db: DB):
    raw = request.cookies.get("refresh_token")
    if raw:
        hashed = hash_token(raw)
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed))
        rt = result.scalar_one_or_none()
        if rt:
            rt.revoked_at = datetime.now(timezone.utc)
    response.delete_cookie("refresh_token")


@router.get("/me", response_model=SellerUserOut)
async def seller_me(user: CurrentSellerUser):
    return user


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, user: CurrentSellerUser, db: DB):
    if not verify_password(body.current_password, user.password_hash):
        raise BadRequestError("Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    return {"message": "Password changed successfully"}
