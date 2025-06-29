
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import service, schema
from db.session import get_db

router = APIRouter(prefix="/cart", tags=["cart"])

@router.get("/{user_id}", response_model=list[schema.CartItemOut])
def get_cart(user_id: int, db: Session = Depends(get_db)):
    return service.get_cart_items(user_id, db)

@router.post("/", response_model=schema.CartItemOut)
def add_item(item: schema.CartItemCreate, db: Session = Depends(get_db)):
    return service.add_to_cart(item, db)

@router.put("/{item_id}", response_model=schema.CartItemOut)
def update_item(item_id: int, item: schema.CartItemUpdate, db: Session = Depends(get_db)):
    updated = service.update_cart_item(item_id, item, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Cart item not found")
    return updated

@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    deleted = service.delete_cart_item(item_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cart item not found")
    return {"message": "Cart item deleted successfully"}
