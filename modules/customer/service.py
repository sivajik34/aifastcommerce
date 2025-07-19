from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.models.customer import Customer
from .schema import CustomerCreate, CustomerUpdate


async def get_customer_by_id(customer_id: int, db: AsyncSession):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()


async def get_customer_by_email(email: str, db: AsyncSession):
    result = await db.execute(
        select(Customer).where(Customer.email == email)
    )
    return result.scalar_one_or_none()


async def create_customer(data: CustomerCreate, db: AsyncSession):
    customer = Customer(**data.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def update_customer(customer_id: int, data: CustomerUpdate, db: AsyncSession):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if customer:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        await db.commit()
        await db.refresh(customer)
    return customer


async def delete_customer(customer_id: int, db: AsyncSession):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()
    if customer:
        await db.delete(customer)
        await db.commit()
    return customer

