from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class InvoiceItem(BaseModel):
    order_item_id: int
    qty: int

class InvoiceInput(BaseModel):
    order_id: int
    items: List[InvoiceItem]  
    comment: str = "Invoice created"
    notify: bool = True 