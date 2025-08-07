from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class LowStockAlertInput(BaseModel):
    threshold: float = Field(default=10.0, description="Stock quantity threshold (e.g., 10)")
    scope_id: int = Field(default=0, description="Website scope ID (usually 0 for default)")
    page_size: int = Field(default=100, description="Number of items per page")

class UpdateStockInput(BaseModel):
    sku: str
    qty: float
    is_in_stock: bool = True  # Optional, defaults to True    