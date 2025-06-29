from sqlalchemy.orm import Session
from db.models.order import Order, OrderItem
from .schema import OrderCreate

def create_order(order_data: OrderCreate, db: Session):
    order = Order(
        user_id=order_data.user_id,
        total_amount=order_data.total_amount,
        status="pending"
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for item in order_data.items:
        db_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(db_item)
    db.commit()
    return order

def get_order_by_id(order_id: int, db: Session):
    return db.query(Order).filter(Order.id == order_id).first()

def get_orders_by_user(user_id: int, db: Session):
    return db.query(Order).filter(Order.user_id == user_id).all()

