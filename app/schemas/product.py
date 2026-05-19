from datetime import datetime
from pydantic import BaseModel, field_validator


class CategoryCreate(BaseModel):
    name_uz: str
    name_ru: str
    parent_id: int | None = None
    image_url: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name_uz: str | None = None
    name_ru: str | None = None
    parent_id: int | None = None
    image_url: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: int
    seller_id: int
    parent_id: int | None
    name_uz: str
    name_ru: str
    slug: str
    image_url: str | None
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class VariantCreate(BaseModel):
    name_uz: str | None = None
    name_ru: str | None = None
    sku: str | None = None
    price: int
    old_price: int | None = None
    stock_quantity: int = 0
    track_stock: bool = True
    attributes: dict = {}
    is_default: bool = False

    @field_validator("price")
    @classmethod
    def check_price(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v


class VariantUpdate(BaseModel):
    name_uz: str | None = None
    name_ru: str | None = None
    price: int | None = None
    old_price: int | None = None
    stock_quantity: int | None = None
    track_stock: bool | None = None
    attributes: dict | None = None
    is_active: bool | None = None


class VariantOut(BaseModel):
    id: int
    product_id: int
    name_uz: str | None
    name_ru: str | None
    sku: str | None
    price: int
    old_price: int | None
    stock_quantity: int
    track_stock: bool
    attributes: dict
    is_default: bool
    is_active: bool

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name_uz: str
    name_ru: str
    description_uz: str | None = None
    description_ru: str | None = None
    category_id: int | None = None
    sku: str | None = None
    is_featured: bool = False
    sort_order: int = 0
    attributes: dict = {}
    variants: list[VariantCreate] = []


class ProductUpdate(BaseModel):
    name_uz: str | None = None
    name_ru: str | None = None
    description_uz: str | None = None
    description_ru: str | None = None
    category_id: int | None = None
    sku: str | None = None
    is_active: bool | None = None
    is_featured: bool | None = None
    sort_order: int | None = None
    attributes: dict | None = None


class ProductImageOut(BaseModel):
    id: int
    url: str
    thumb_url: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class ProductOut(BaseModel):
    id: int
    seller_id: int
    category_id: int | None
    name_uz: str
    name_ru: str
    description_uz: str | None
    description_ru: str | None
    sku: str | None
    is_active: bool
    is_featured: bool
    sort_order: int
    attributes: dict
    variants: list[VariantOut] = []
    images: list[ProductImageOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductListOut(BaseModel):
    id: int
    name_uz: str
    name_ru: str
    category_id: int | None
    is_active: bool
    is_featured: bool
    sort_order: int
    variants: list[VariantOut] = []
    images: list[ProductImageOut] = []

    model_config = {"from_attributes": True}
