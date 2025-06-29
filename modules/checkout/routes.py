from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import service, schema
from db.session import get_db

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=schema.OrderOut)
def create_order(order: schema.OrderCreate, db: Session = Depends(get_db)):
    return service.create_order(order, db)

@router.get("/{order_id}", response_model=schema.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    db_order = service.get_order_by_id(order_id, db)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@router.get("/user/{user_id}", response_model=list[schema.OrderOut])
def get_user_orders(user_id: int, db: Session = Depends(get_db)):
    return service.get_orders_by_user(user_id, db)

