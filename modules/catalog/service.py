from sqlalchemy import select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.product import Product
from .schema import ProductCreate, ProductUpdate
from typing import Optional, List

async def get_all_products(db: AsyncSession):
    result = await db.execute(select(Product))
    return result.scalars().all()


async def get_product_by_id(product_id: int, db: AsyncSession):
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(product: ProductCreate, db: AsyncSession):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


async def update_product(product_id: int, product: ProductUpdate, db: AsyncSession):
    result = await db.execute(select(Product).where(Product.id == product_id))
    db_product = result.scalar_one_or_none()
    if db_product:
        for key, value in product.model_dump().items():
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


from sqlalchemy.orm import selectinload

async def search_catalog_products(
    db: AsyncSession,
    query: str,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = "relevance",
    limit: Optional[int] = 10
) -> List[Product]:
    stmt = select(Product).options(selectinload(Product.category))

    filters = []

    if query:
        filters.append(Product.name.ilike(f"%{query}%"))
    if category_id is not None:
        filters.append(Product.category_id == category_id)
    if min_price is not None:
        filters.append(Product.price >= min_price)
    if max_price is not None:
        filters.append(Product.price <= max_price)

    if filters:
        stmt = stmt.where(and_(*filters))

    if sort_by == "price_asc":
        stmt = stmt.order_by(asc(Product.price))
    elif sort_by == "price_desc":
        stmt = stmt.order_by(desc(Product.price))
    elif sort_by == "rating":
        stmt = stmt.order_by(desc(Product.average_rating))
    elif sort_by == "newest":
        stmt = stmt.order_by(desc(Product.created_at))
    else:
        stmt = stmt.order_by(desc(Product.created_at))

    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


async def get_products_by_category(
    category_id: int, db: AsyncSession
) -> List[Product]:
    stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.category_id == category_id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
