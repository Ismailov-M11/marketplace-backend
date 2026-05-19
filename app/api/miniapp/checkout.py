from datetime import datetime, timezone

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentCustomer
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.bot import BotSettings, Bot
from app.models.customer import Cart, Customer, CustomerAddress
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.product import ProductVariant
from app.schemas.order import PlaceOrderRequest

router = APIRouter()


def _generate_order_number(seller_id: int) -> str:
    from datetime import datetime, timezone
    import random
    now = datetime.now(timezone.utc)
    return f"{now.year}-{random.randint(100000, 999999)}"


@router.post("/checkout/place-order", status_code=status.HTTP_201_CREATED)
async def place_order(body: PlaceOrderRequest, customer: CurrentCustomer, db: DB):
    # Get cart
    cart_result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.customer_id == customer.id)
    )
    cart = cart_result.scalar_one_or_none()
    if not cart or not cart.items:
        raise BadRequestError("Cart is empty")

    # Get bot settings for delivery fee
    bot_result = await db.execute(
        select(Bot).where(Bot.seller_id == customer.seller_id, Bot.is_active == True)
    )
    bot = bot_result.scalar_one_or_none()
    bot_settings = None
    if bot:
        settings_result = await db.execute(select(BotSettings).where(BotSettings.bot_id == bot.id))
        bot_settings = settings_result.scalar_one_or_none()

    # Validate stock and build order items
    subtotal = 0
    order_items_data = []
    for item in cart.items:
        variant_result = await db.execute(
            select(ProductVariant).where(ProductVariant.id == item.variant_id)
        )
        variant = variant_result.scalar_one_or_none()
        if not variant or not variant.is_active:
            raise BadRequestError(f"Variant {item.variant_id} unavailable")
        if variant.track_stock and variant.stock_quantity < item.quantity:
            raise BadRequestError(f"Insufficient stock for variant {item.variant_id}")

        item_total = variant.price * item.quantity
        subtotal += item_total
        order_items_data.append({
            "variant": variant,
            "quantity": item.quantity,
            "price": variant.price,
            "total": item_total,
        })

    # Calculate delivery fee
    delivery_fee = 0
    if body.delivery_method == "courier" and bot_settings:
        if bot_settings.free_delivery_from and subtotal >= bot_settings.free_delivery_from:
            delivery_fee = 0
        else:
            delivery_fee = bot_settings.delivery_fee or 0

    total = subtotal + delivery_fee

    # Get address text
    address_text = body.address
    if body.address_id and not address_text:
        addr_result = await db.execute(
            select(CustomerAddress).where(
                CustomerAddress.id == body.address_id,
                CustomerAddress.customer_id == customer.id,
            )
        )
        addr = addr_result.scalar_one_or_none()
        if addr:
            address_text = addr.address

    # Create order
    order = Order(
        seller_id=customer.seller_id,
        customer_id=customer.id,
        order_number=_generate_order_number(customer.seller_id),
        status="new",
        payment_status="pending",
        payment_method=body.payment_method,
        delivery_method=body.delivery_method,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=total,
        currency="UZS",
        address_text=address_text,
        address_lat=body.address_lat,
        address_lng=body.address_lng,
        customer_name=customer.full_name or "Customer",
        customer_phone=customer.phone or "",
        customer_comment=body.comment,
    )
    db.add(order)
    await db.flush()

    # Create order items and reduce stock
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

    # Status history
    db.add(OrderStatusHistory(
        order_id=order.id, seller_id=customer.seller_id,
        to_status="new", changed_by=f"customer:{customer.id}",
    ))

    # Clear cart
    for item in cart.items:
        await db.delete(item)

    # Update customer stats
    customer.total_orders += 1
    customer.total_spent += total
    customer.last_order_at = datetime.now(timezone.utc)

    await db.flush()

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "total": order.total,
        "status": order.status,
    }
