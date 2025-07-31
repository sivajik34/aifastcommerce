from pydantic import BaseModel
from typing import List, Optional

class CreateCategoryInput(BaseModel):
    name: str
    parent_id: Optional[int] = 2  # Default: under "Default Category" (id=2)
    is_active: Optional[bool] = True
    include_in_menu: Optional[bool] = True

class AssignCategoryInput(BaseModel):
    sku: str
    category_ids: List[int]