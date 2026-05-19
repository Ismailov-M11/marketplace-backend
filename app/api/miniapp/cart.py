from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentCustomer
from app.core.exceptions import BadRequestError, NotFoundError
from app.models.customer import Cart, CartItem
from app.models.product import ProductVariant
from app.schemas.order import CartItemAdd, CartItemUpdate, CartOut

router = APIRouter()


async def _get_or_create_cart(customer, db) -> Cart:
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.customer_id == customer.id)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(customer_id=customer.id, seller_id=customer.seller_id)
        db.add(cart)
        await db.flush()
    return cart


@router.get("/cart", response_model=CartOut)
async def get_cart(customer: CurrentCustomer, db: DB):
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.customer_id == customer.id)
    )
    cart = result.scalar_one_or_none()
    if not cart:
        return CartOut(id=0, items=[], subtotal=0)

    subtotal = sum(i.price_snapshot * i.quantity for i in cart.items)
    return CartOut(id=cart.id, items=cart.items, subtotal=subtotal)


@router.post("/cart/items", status_code=status.HTTP_201_CREATED)
async def add_to_cart(body: CartItemAdd, customer: CurrentCustomer, db: DB):
    variant_result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.id == body.variant_id,
            ProductVariant.seller_id == customer.seller_id,
            ProductVariant.is_active == True,
            ProductVariant.deleted_at.is_(None),
        )
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise NotFoundError("Variant not found")
    if variant.track_stock and variant.stock_quantity < body.quantity:
        raise BadRequestError("Not enough stock")

    cart = await _get_or_create_cart(customer, db)

    existing = next((i for i in cart.items if i.variant_id == body.variant_id), None)
    if existing:
        existing.quantity += body.quantity
        existing.price_snapshot = variant.price
    else:
        db.add(CartItem(
            cart_id=cart.id,
            variant_id=body.variant_id,
            quantity=body.quantity,
            price_snapshot=variant.price,
        ))

    return {"message": "Added to cart"}


@router.patch("/cart/items/{item_id}")
async def update_cart_item(item_id: int, body: CartItemUpdate, customer: CurrentCustomer, db: DB):
    cart = await _get_or_create_cart(customer, db)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise NotFoundError("Cart item not found")
    if body.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = body.quantity
    return {"message": "Cart updated"}


@router.delete("/cart/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cart_item(item_id: int, customer: CurrentCustomer, db: DB):
    cart = await _get_or_create_cart(customer, db)
    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        raise NotFoundError("Cart item not found")
    await db.delete(item)


@router.delete("/cart", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(customer: CurrentCustomer, db: DB):
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.customer_id == customer.id)
    )
    cart = result.scalar_one_or_none()
    if cart:
        for item in cart.items:
            await db.delete(item)
