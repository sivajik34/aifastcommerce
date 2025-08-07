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

class ShipmentTrackInput(BaseModel):
    order_id: int
    parent_id: int  # this is the shipment ID
    track_number: str
    title: str
    carrier_code: str
    weight: Optional[float] = 0.0
    qty: Optional[int] = 1
    description: Optional[str] = ""
    created_at: Optional[str] = None  # ISO format recommended
    updated_at: Optional[str] = None