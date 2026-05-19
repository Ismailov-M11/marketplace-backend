from fastapi import APIRouter, Header
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB
from app.core.exceptions import ForbiddenError, BadRequestError
from app.core.security import hash_password
from app.models.admin_user import AdminUser
from app.settings import settings

router = APIRouter()

SETUP_SECRET = "marketplace-setup-2026"


class CreateAdminRequest(BaseModel):
    secret: str
    email: str
    password: str
    full_name: str = "Super Admin"


@router.post("/setup/create-admin")
async def create_first_admin(body: CreateAdminRequest, db: DB):
    if settings.is_production and body.secret != SETUP_SECRET:
        raise ForbiddenError("Invalid setup secret")

    existing = (await db.execute(select(AdminUser))).scalars().first()
    if existing:
        raise BadRequestError("Admin user already exists. Delete this endpoint.")

    admin = AdminUser(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role="super_admin",
        is_active=True,
        totp_enabled=False,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)

    return {
        "message": "Admin created successfully",
        "id": admin.id,
        "email": admin.email,
        "role": admin.role,
    }
