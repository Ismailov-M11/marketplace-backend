from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import select, update

from app.api.deps import DB, CurrentAdmin
from app.core.exceptions import UnauthorizedError, BadRequestError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from app.models.admin_user import AdminUser
from app.models.audit import RefreshToken
from app.schemas.auth import AdminUserOut, LoginRequest, TokenResponse
from app.settings import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def admin_login(body: LoginRequest, request: Request, response: Response, db: DB):
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == body.email, AdminUser.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")

    if user.totp_enabled:
        if not body.totp_code:
            raise BadRequestError("TOTP code required")
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(body.totp_code):
            raise UnauthorizedError("Invalid TOTP code")

    # Update last login
    await db.execute(
        update(AdminUser)
        .where(AdminUser.id == user.id)
        .values(last_login_at=datetime.now(timezone.utc))
    )

    access_token = create_access_token({
        "sub": user.id, "type": "admin", "role": user.role
    })
    raw_refresh, hashed_refresh = create_refresh_token()

    db.add(RefreshToken(
        user_type="admin",
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
async def admin_refresh(request: Request, response: Response, db: DB):
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise UnauthorizedError("No refresh token")

    hashed = hash_token(raw)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hashed,
            RefreshToken.user_type == "admin",
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise UnauthorizedError("Invalid or expired refresh token")

    # Revoke old, issue new
    rt.revoked_at = datetime.now(timezone.utc)
    await db.flush()

    user_result = await db.execute(
        select(AdminUser).where(AdminUser.id == rt.user_id, AdminUser.is_active == True)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")

    access_token = create_access_token({"sub": user.id, "type": "admin", "role": user.role})
    new_raw, new_hashed = create_refresh_token()

    db.add(RefreshToken(
        user_type="admin",
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
async def admin_logout(request: Request, response: Response, db: DB):
    raw = request.cookies.get("refresh_token")
    if raw:
        hashed = hash_token(raw)
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed))
        rt = result.scalar_one_or_none()
        if rt:
            rt.revoked_at = datetime.now(timezone.utc)
    response.delete_cookie("refresh_token")


@router.get("/me", response_model=AdminUserOut)
async def admin_me(user: CurrentAdmin):
    return user
