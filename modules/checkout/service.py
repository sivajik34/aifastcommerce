from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert
from db.models.order import Order, OrderItem
from .schema import OrderCreate


async def create_order(order_data: OrderCreate, db: AsyncSession):
    order = Order(
        user_id=order_data.user_id,
        total_amount=order_data.total_amount,
        status="pending"
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    for item in order_data.items:
        db_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(db_item)

    await db.commit()
    return order


async def get_order_by_id(order_id: int, db: AsyncSession):
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def get_orders_by_user(user_id: int, db: AsyncSession):
    result = await db.execute(select(Order).where(Order.user_id == user_id))
    return result.scalars().all()
