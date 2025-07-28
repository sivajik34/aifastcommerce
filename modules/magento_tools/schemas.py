from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
   
class MagentoAPIBase(BaseModel):
    store_view_code: Optional[str] = "default"
    api_version: Optional[str] = "v1"

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

class ViewProductInput(MagentoAPIBase):
    sku: str 

class CreateProductInput(BaseModel):
    sku: str
    name: str
    price: float
    status: int  # 1 = Enabled, 2 = Disabled
    type_id: str = "simple"
    attribute_set_id: int = 4  # Default attribute set
    weight: Optional[float] = 1.0
    visibility: int = 4  # 4 = Catalog, Search
    qty: Optional[float] = 0
    is_in_stock: Optional[bool] = True

class UpdateProductInput(BaseModel):
    sku: str
    name: Optional[str] = None
    price: Optional[float] = None
    status: Optional[int] = None  # 1 = Enabled, 2 = Disabled
    visibility: Optional[int] = None  # 1 = Not visible, 2 = Catalog, 3 = Search, 4 = Catalog/Search
    weight: Optional[float] = None
    qty: Optional[float] = None
    is_in_stock: Optional[bool] = None

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

class InvoiceItem(BaseModel):
    order_item_id: int
    qty: int

class InvoiceInput(BaseModel):
    order_id: int
    items: List[InvoiceItem]  
    comment: str = "Invoice created"
    notify: bool = True 

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

class CreateCategoryInput(BaseModel):
    name: str
    parent_id: Optional[int] = 2  # Default: under "Default Category" (id=2)
    is_active: Optional[bool] = True
    include_in_menu: Optional[bool] = True

class AssignCategoryInput(BaseModel):
    sku: str
    category_ids: List[int]

      