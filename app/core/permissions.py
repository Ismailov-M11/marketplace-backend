from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.admin_user import AdminUser
from app.models.seller import Seller, SellerUser

security = HTTPBearer(auto_error=False)

PERMISSIONS: dict[str, list[str]] = {
    "super_admin": ["*"],
    "operator": [
        "application.read", "application.approve", "application.reject",
        "seller.read", "bot.read",
    ],
    "support": ["*.read", "audit.read"],
    "owner": ["*"],
    "manager": [
        "product.*", "order.*", "customer.read",
        "broadcast.*", "category.*",
    ],
    "warehouse": [
        "product.read", "product.update_stock",
        "order.read", "order.update_status",
    ],
}


def has_permission(role: str, perm: str) -> bool:
    perms = PERMISSIONS.get(role, [])
    if "*" in perms:
        return True
    if perm in perms:
        return True
    # wildcard match like "product.*"
    perm_ns = perm.split(".")[0]
    if f"{perm_ns}.*" in perms:
        return True
    if "*.read" in perms and perm.endswith(".read"):
        return True
    return False


async def _get_token(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if not credentials:
        raise UnauthorizedError("Missing auth token")
    try:
        return decode_token(credentials.credentials)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")


async def current_admin_user(
    payload: Annotated[dict, Depends(_get_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUser:
    if payload.get("type") != "admin":
        raise ForbiddenError("Admin access required")
    user_id = payload.get("sub")
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id, AdminUser.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found or inactive")
    return user


async def current_seller_user(
    payload: Annotated[dict, Depends(_get_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SellerUser:
    if payload.get("type") != "seller":
        raise ForbiddenError("Seller access required")
    user_id = payload.get("sub")
    result = await db.execute(
        select(SellerUser).where(SellerUser.id == user_id, SellerUser.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found or inactive")
    return user


async def current_seller(
    user: Annotated[SellerUser, Depends(current_seller_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Seller:
    result = await db.execute(
        select(Seller).where(Seller.id == user.seller_id, Seller.status == "active")
    )
    seller = result.scalar_one_or_none()
    if not seller:
        raise ForbiddenError("Seller account not found or suspended")
    return seller


async def current_miniapp_customer(
    payload: Annotated[dict, Depends(_get_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if payload.get("type") != "miniapp":
        raise ForbiddenError("Mini App access required")
    from app.models.customer import Customer
    customer_id = payload.get("customer_id")
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise UnauthorizedError("Customer not found")
    return customer


def require_permission(perm: str):
    async def dep(user: Annotated[SellerUser, Depends(current_seller_user)]) -> SellerUser:
        if not has_permission(user.role, perm):
            raise ForbiddenError(f"Permission '{perm}' required")
        return user
    return dep


def require_admin_role(*roles: str):
    async def dep(user: Annotated[AdminUser, Depends(current_admin_user)]) -> AdminUser:
        if user.role not in roles and user.role != "super_admin":
            raise ForbiddenError(f"Role {roles} required")
        return user
    return dep
