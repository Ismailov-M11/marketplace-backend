from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import DB
from app.core.security import hash_password
from app.models.seller import SellerApplication
from app.schemas.seller import ApplicationCreate, ApplicationOut
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.post("/applications", status_code=status.HTTP_201_CREATED)
async def submit_application(body: ApplicationCreate, db: DB) -> dict:
    app_obj = SellerApplication(
        status="pending",
        full_name=body.full_name,
        phone=body.phone,
        email=body.email,
        company_name=body.company_name,
        inn=body.inn,
        legal_name=body.legal_name,
        mfo=body.mfo,
        account_number=body.account_number,
        oked=body.oked,
        password_hash=hash_password(body.password),
        business_type=body.business_type,
        desired_usernames=body.desired_usernames,
        category=body.category,
        description=body.description,
        monthly_orders=body.monthly_orders,
        referrer=body.referrer,
    )
    db.add(app_obj)
    await db.flush()
    await db.refresh(app_obj)
    return {"id": app_obj.id, "status": app_obj.status, "message": "Application submitted successfully"}


@router.get("/applications/{application_id}/status")
async def get_application_status(application_id: int, db: DB) -> dict:
    result = await db.execute(
        select(SellerApplication).where(SellerApplication.id == application_id)
    )
    app_obj = result.scalar_one_or_none()
    if not app_obj:
        raise NotFoundError("Application not found")
    return {"id": app_obj.id, "status": app_obj.status}
