
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import service, schema
from db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/", response_model=list[schema.ProductOut])
async def read_products(db: AsyncSession = Depends(get_db)):
    return await service.get_all_products(db)

@router.get("/{product_id}", response_model=schema.ProductOut)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    db_product = await service.get_product_by_id(product_id, db)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.post("/", response_model=schema.ProductOut)
async def create_product(product: schema.ProductCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_product(product, db)

@router.put("/{product_id}", response_model=schema.ProductOut)
async def update_product(product_id: int, product: schema.ProductUpdate, db: AsyncSession = Depends(get_db)):
    updated_product = await service.update_product(product_id, product, db)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product

@router.delete("/{product_id}")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    deleted_product = await service.delete_product(product_id, db)
    if not deleted_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}
