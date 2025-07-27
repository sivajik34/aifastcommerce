from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
   

class ViewCustomerInput(BaseModel):
    email: EmailStr

class AddressInput(BaseModel):
    firstname: str
    lastname: str
    street: List[str]
    city: str
    region: Optional[str]
    region_id: Optional[int]
    postcode: str
    country_id: Literal["IN", "US", "UK", "CA", "AU"]  # Add more as needed
    telephone: str
    default_shipping: Optional[bool] = False
    default_billing: Optional[bool] = False

class CreateCustomerInput(BaseModel):
    email: EmailStr
    firstname:str
    lastname:str
    password:Optional[str] = None
    store_view_code: Optional[str] = "default"
    website_id: Optional[int] = 1
    store_id: Optional[int] = 1
    group_id: Optional[int] = 1
    address: Optional[AddressInput] = None

class ViewProductInput(BaseModel):
    sku: str 
    
class SearchProductsInput(BaseModel):
    query: Optional[str] = Field(description="Search query for products")
    category_id: Optional[int] = Field(default=None, description="Filter by category")
    min_price: Optional[float] = Field(default=None, description="Minimum price filter")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter")
    sort_by: Optional[str] = Field(default="relevance", description="Sort by: relevance, price_asc, price_desc, rating, newest")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")

class UpdateStockInput(BaseModel):
    sku: str
    qty: float
    is_in_stock: bool = True  # Optional, defaults to True

class OrderItem(BaseModel):
    sku: str
    qty: int

class CreateOrderInput(BaseModel):
    customer_email: EmailStr
    firstname: str
    lastname: str
    items: List[OrderItem]
    payment_method: Literal["checkmo", "banktransfer", "cashondelivery"] = "checkmo"