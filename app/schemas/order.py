from datetime import datetime
from pydantic import BaseModel


class OrderItemOut(BaseModel):
    id: int
    variant_id: int | None
    product_name_snap: str
    variant_name_snap: str | None
    sku_snap: str | None
    price_snap: int
    quantity: int
    total: int

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    seller_id: int
    customer_id: int
    order_number: str
    status: str
    payment_status: str
    payment_method: str
    delivery_method: str
    subtotal: int
    delivery_fee: int
    discount: int
    total: int
    currency: str
    address_text: str | None
    customer_name: str
    customer_phone: str
    customer_comment: str | None
    internal_note: str | None
    items: list[OrderItemOut] = []
    created_at: datetime
    confirmed_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    cancelled_at: datetime | None

    model_config = {"from_attributes": True}


class OrderListOut(BaseModel):
    id: int
    order_number: str
    status: str
    payment_status: str
    total: int
    currency: str
    customer_name: str
    customer_phone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateOrderStatus(BaseModel):
    status: str
    note: str | None = None


class PlaceOrderRequest(BaseModel):
    address_id: int | None = None
    address: str | None = None
    address_lat: float | None = None
    address_lng: float | None = None
    payment_method: str
    delivery_method: str
    comment: str | None = None
    promo_code: str | None = None


class CartItemAdd(BaseModel):
    variant_id: int
    quantity: int


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemOut(BaseModel):
    id: int
    variant_id: int
    quantity: int
    price_snapshot: int

    model_config = {"from_attributes": True}


class CartOut(BaseModel):
    id: int
    items: list[CartItemOut] = []
    subtotal: int = 0

    model_config = {"from_attributes": True}
