from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models.category import Category
from .category_schema import CategoryCreate, CategoryUpdate


async def create_category(category: CategoryCreate, db: AsyncSession):
    db_category = Category(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category


async def get_category_by_id(category_id: int, db: AsyncSession):
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def get_all_categories(db: AsyncSession):
    result = await db.execute(select(Category))
    return result.scalars().all()


async def update_category(category_id: int, update: CategoryUpdate, db: AsyncSession):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category:
        for key, value in update.model_dump(exclude_unset=True).items():
            setattr(category, key, value)
        await db.commit()
        await db.refresh(category)
    return category


async def delete_category(category_id: int, db: AsyncSession):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category:
        await db.delete(category)
        await db.commit()
    return category
