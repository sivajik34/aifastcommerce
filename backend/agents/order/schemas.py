from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal

class OrderItem(BaseModel):
    sku: str
    qty: int

class CreateOrderInput(BaseModel):
    customer_email: EmailStr
    firstname: str
    lastname: str
    items: List[OrderItem]
    payment_method: Literal["checkmo", "banktransfer", "cashondelivery"] = "checkmo"

class GetOrderByIncrementIdInput(BaseModel):
    increment_id: str

class GetOrderIdInput(BaseModel):
    increment_id: str

class CancelOrderInput(BaseModel):
    order_id: int
    comment: Optional[str] = "Order cancelled via assistant"

class GetOrdersInput(BaseModel):
    status: Optional[str] = None
    payment_method: Optional[str] = None
    page_size: Optional[int] = 10
    current_page: Optional[int] = 1
    last_n_days: Optional[int] = None





 