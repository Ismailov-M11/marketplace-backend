from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import (
    current_admin_user,
    current_miniapp_customer,
    current_seller,
    current_seller_user,
)
from app.models.admin_user import AdminUser
from app.models.customer import Customer
from app.models.seller import Seller, SellerUser

DB = Annotated[AsyncSession, Depends(get_db)]
CurrentAdmin = Annotated[AdminUser, Depends(current_admin_user)]
CurrentSellerUser = Annotated[SellerUser, Depends(current_seller_user)]
CurrentSeller = Annotated[Seller, Depends(current_seller)]
CurrentCustomer = Annotated[Customer, Depends(current_miniapp_customer)]


class Pagination:
    def __init__(self, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
        self.page = page
        self.limit = limit
        self.offset = (page - 1) * limit

Paginate = Annotated[Pagination, Depends(Pagination)]
