
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProductBase(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category_id:Optional[int] = None
   
    

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    created_at: datetime
    average_rating: Optional[float] = None
    review_count: Optional[int]

    class Config:
        from_attributes = True
