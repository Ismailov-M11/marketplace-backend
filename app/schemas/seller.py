from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, EmailStr, field_validator
import re


def validate_inn(v: str) -> str:
    if not re.match(r"^\d{9}(\d{5})?$", v):
        raise ValueError("INN must be 9 or 14 digits")
    return v


def validate_phone(v: str) -> str:
    clean = re.sub(r"[\s\-\(\)]", "", v)
    if not re.match(r"^\+998\d{9}$", clean):
        raise ValueError("Phone must be in format +998XXXXXXXXX")
    return clean


class ApplicationCreate(BaseModel):
    full_name: str
    phone: str
    email: EmailStr
    company_name: str
    inn: str
    business_type: str | None = None
    desired_usernames: list[str]
    category: str | None = None
    description: str | None = None
    monthly_orders: str | None = None
    referrer: str | None = None

    @field_validator("inn")
    @classmethod
    def check_inn(cls, v: str) -> str:
        return validate_inn(v)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone(v)

    @field_validator("desired_usernames")
    @classmethod
    def check_usernames(cls, v: list[str]) -> list[str]:
        if len(v) < 1 or len(v) > 3:
            raise ValueError("Provide 1 to 3 desired usernames")
        for u in v:
            if not re.match(r"^[a-z0-9_]{5,32}bot$", u, re.IGNORECASE):
                raise ValueError(f"Username '{u}' must be 5-32 chars, end with 'bot'")
        return v


class ApplicationOut(BaseModel):
    id: int
    status: str
    full_name: str
    phone: str
    email: str
    company_name: str
    inn: str
    category: str | None
    desired_usernames: list[str]
    created_at: datetime
    reviewed_at: datetime | None
    seller_id: int | None

    model_config = {"from_attributes": True}


class ApplicationApprove(BaseModel):
    username: str
    telegram_token: str
    plan: str = "free"
    owner_password: str | None = None


class ApplicationReject(BaseModel):
    reason: str


class SellerOut(BaseModel):
    id: int
    slug: str
    company_name: str
    display_name: str
    inn: str
    phone: str
    email: str
    status: str
    plan: str
    commission_pct: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class SellerUpdate(BaseModel):
    display_name: str | None = None
    phone: str | None = None
    legal_address: str | None = None
    status: str | None = None
    plan: str | None = None
    commission_pct: Decimal | None = None


class SellerPublicOut(BaseModel):
    id: int
    slug: str
    display_name: str
    phone: str | None = None

    model_config = {"from_attributes": True}
