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