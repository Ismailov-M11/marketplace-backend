from fastapi import APIRouter, File, UploadFile, status
from sqlalchemy import select

from app.api.deps import DB
from app.core.security import hash_password
from app.core.storage import upload_image, is_storage_configured
from app.core.exceptions import NotFoundError, BadRequestError
from app.models.seller import SellerApplication
from app.schemas.seller import ApplicationCreate

router = APIRouter()


@router.post("/upload-image")
async def upload_application_image(file: UploadFile = File(...)) -> dict:
    """Public endpoint — uploads an image for use in step 3 of the application form."""
    if not is_storage_configured():
        raise BadRequestError("File storage is not configured on this server")
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise BadRequestError("Only JPEG, PNG, WEBP or GIF images are accepted")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise BadRequestError("Image must be under 10 MB")
    url, _ = await upload_image(data, folder="applications")
    return {"url": url}


@router.post("/applications", status_code=status.HTTP_201_CREATED)
async def submit_application(body: ApplicationCreate, db: DB) -> dict:
    initial_data = None
    if any([
        body.initial_catalog_name_uz,
        body.initial_catalog_name_ru,
        body.initial_product_name_uz,
        body.initial_product_name_ru,
    ]):
        initial_data = {
            "catalog_name_uz": body.initial_catalog_name_uz,
            "catalog_name_ru": body.initial_catalog_name_ru,
            "product_name_uz": body.initial_product_name_uz,
            "product_name_ru": body.initial_product_name_ru,
            "product_description_uz": body.initial_product_description_uz,
            "product_description_ru": body.initial_product_description_ru,
            "product_sku": body.initial_product_sku,
            "product_is_featured": body.initial_product_is_featured,
            "product_image": body.initial_product_image,
            "product_variants": body.initial_product_variants,
        }

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
        initial_data=initial_data,
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
