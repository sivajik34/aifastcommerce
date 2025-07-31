from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ShipmentItem(BaseModel):
    order_item_id: int
    qty: int


class ShipmentInput(BaseModel):
    order_id: int
    items: List[ShipmentItem]
    notify: bool = True
    carrier_code: str = "custom"
    track_number: str = "N/A"
    title: str = "Standard Shipping"