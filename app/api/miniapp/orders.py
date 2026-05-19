"""Direct order placement (no cart sync required) + customer order history."""
import random
from datetime import datetime, timezone

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentCustomer
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.bot import Bot, BotSettings
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.product import ProductVariant

router = APIRouter()


class DirectOrderItem(BaseModel):
    variant_id: int
    quantity: int


class DirectOrderRequest(BaseModel):
    phone: str
    delivery_address: str
    comment: str | None = None
    items: list[DirectOrderItem]


def _gen_order_number() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{random.randint(100000, 999999)}"


@router.post("/orders/direct", status_code=status.HTTP_201_CREATED)
async def place_direct_order(body: DirectOrderRequest, customer: CurrentCustomer, db: DB):
    if not body.items:
        raise BadRequestError("No items provided")

    bot_result = await db.execute(
        select(Bot).where(Bot.seller_id == customer.seller_id, Bot.is_active == True)
    )
    bot = bot_result.scalar_one_or_none()
    bot_settings = None
    if bot:
        settings_result = await db.execute(select(BotSettings).where(BotSettings.bot_id == bot.id))
        bot_settings = settings_result.scalar_one_or_none()

    subtotal = 0
    order_items_data = []
    for item in body.items:
        variant_result = await db.execute(
            select(ProductVariant).where(ProductVariant.id == item.variant_id)
        )
        variant = variant_result.scalar_one_or_none()
        if not variant or not variant.is_active:
            raise BadRequestError(f"Variant {item.variant_id} is not available")
        if variant.track_stock and variant.stock_quantity < item.quantity:
            raise BadRequestError(f"Insufficient stock for variant {item.variant_id}")

        item_total = variant.price * item.quantity
        subtotal += item_total
        order_items_data.append({"variant": variant, "quantity": item.quantity, "price": variant.price, "total": item_total})

    delivery_fee = 0
    if bot_settings:
        if bot_settings.free_delivery_from and subtotal >= bot_settings.free_delivery_from:
            delivery_fee = 0
        else:
            delivery_fee = bot_settings.delivery_fee or 0

    total = subtotal + delivery_fee

    # Update customer phone if provided and not already set
    if body.phone and not customer.phone:
        cust = await db.get(Customer, customer.id)
        if cust:
            cust.phone = body.phone

    order = Order(
        seller_id=customer.seller_id,
        customer_id=customer.id,
        order_number=_gen_order_number(),
        status="new",
        payment_status="pending",
        payment_method="cash",
        delivery_method="courier",
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=total,
        currency="UZS",
        address_text=body.delivery_address,
        customer_name=customer.full_name or "Customer",
        customer_phone=body.phone,
        customer_comment=body.comment,
    )
    db.add(order)
    await db.flush()

    for item_data in order_items_data:
        variant = item_data["variant"]
        db.add(OrderItem(
            order_id=order.id,
            seller_id=customer.seller_id,
            variant_id=variant.id,
            product_name_snap=f"Product {variant.product_id}",
            price_snap=item_data["price"],
            quantity=item_data["quantity"],
            total=item_data["total"],
        ))
        if variant.track_stock:
            variant.stock_quantity -= item_data["quantity"]

    db.add(OrderStatusHistory(
        order_id=order.id, seller_id=customer.seller_id,
        to_status="new", changed_by=f"customer:{customer.id}",
    ))

    cust_obj = await db.get(Customer, customer.id)
    if cust_obj:
        cust_obj.total_orders = (cust_obj.total_orders or 0) + 1
        cust_obj.total_spent = (cust_obj.total_spent or 0) + total
        cust_obj.last_order_at = datetime.now(timezone.utc)

    await db.flush()

    return {"id": order.id, "order_number": order.order_number, "total": order.total, "status": order.status}


@router.get("/orders")
async def list_orders(customer: CurrentCustomer, db: DB):
    result = await db.execute(
        select(Order)
        .where(Order.customer_id == customer.id, Order.seller_id == customer.seller_id)
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    orders = result.scalars().all()
    return [
        {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status,
            "total": o.total,
            "items_count": 0,
            "created_at": o.created_at,
        }
        for o in orders
    ]


@router.get("/orders/{order_id}")
async def get_order(order_id: int, customer: CurrentCustomer, db: DB):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.customer_id == customer.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise NotFoundError("Order not found")
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "total": order.total,
        "subtotal": order.subtotal,
        "delivery_fee": order.delivery_fee,
        "delivery_address": order.address_text,
        "comment": order.customer_comment,
        "created_at": order.created_at,
        "items": [
            {
                "id": item.id,
                "product_name": item.product_name_snap,
                "variant_name": getattr(item, "variant_name_snap", ""),
                "quantity": item.quantity,
                "price_snap": item.price_snap,
            }
            for item in order.items
        ],
    }


@router.get("/profile")
async def get_profile(customer: CurrentCustomer, db: DB):
    result = await db.execute(select(Customer).where(Customer.id == customer.id))
    cust = result.scalar_one_or_none()
    if not cust:
        raise NotFoundError("Customer not found")
    return {
        "id": cust.id,
        "first_name": (cust.full_name or "").split(" ")[0],
        "last_name": " ".join((cust.full_name or "").split(" ")[1:]) or None,
        "phone": cust.phone,
        "orders_count": cust.total_orders or 0,
        "total_spent": cust.total_spent or 0,
    }
