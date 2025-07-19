from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update

from db.models.cart import CartItem
from .schema import CartItemCreate, CartItemUpdate


async def get_cart_items(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(CartItem).where(CartItem.user_id == user_id)
    )
    return result.scalars().all()


async def add_to_cart(item: CartItemCreate, db: AsyncSession):
    db_item = CartItem(**item.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def update_cart_item(item_id: int, item: CartItemUpdate, db: AsyncSession):
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id)
    )
    db_item = result.scalar_one_or_none()
    if db_item:
        db_item.quantity = item.quantity
        await db.commit()
        await db.refresh(db_item)
    return db_item


async def delete_cart_item(item_id: int, db: AsyncSession):
    result = await db.execute(
        select(CartItem).where(CartItem.id == item_id)
    )
    db_item = result.scalar_one_or_none()
    if db_item:
        await db.delete(db_item)
        await db.commit()
    return db_item
