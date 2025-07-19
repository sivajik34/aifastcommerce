from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from db.session import get_db
from db.models.category import Category
from modules.catalog.category_schema import CategoryCreate, CategoryUpdate, CategoryOut
from modules.catalog.category_service import (
    create_category,
    get_category_by_id,
    get_all_categories,
    update_category,
    delete_category,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryOut)
async def create_new_category(
    category: CategoryCreate, db: AsyncSession = Depends(get_db)
):
    return await create_category(category, db)


@router.get("/", response_model=List[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await get_all_categories(db)


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    db_category = await get_category_by_id(category_id, db)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category


@router.put("/{category_id}", response_model=CategoryOut)
async def update_existing_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    db_category = await update_category(category_id, category_update, db)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category


@router.delete("/{category_id}")
async def delete_existing_category(
    category_id: int, db: AsyncSession = Depends(get_db)
):
    db_category = await delete_category(category_id, db)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": f"Category with ID {category_id} deleted successfully"}
