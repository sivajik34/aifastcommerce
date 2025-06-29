from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.product import Product
from .schema import ProductCreate, ProductUpdate


async def get_all_products(db: AsyncSession):
    result = await db.execute(select(Product))
    return result.scalars().all()


async def get_product_by_id(product_id: int, db: AsyncSession):
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(product: ProductCreate, db: AsyncSession):
    db_product = Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


async def update_product(product_id: int, product: ProductUpdate, db: AsyncSession):
    result = await db.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    if db_product:
        for key, value in product.dict().items():
            setattr(db_product, key, value)
        await db.commit()
        await db.refresh(db_product)
    return db_product


async def delete_product(product_id: int, db: AsyncSession):
    result = await db.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    if db_product:
        await db.delete(db_product)
        await db.commit()
    return db_product
