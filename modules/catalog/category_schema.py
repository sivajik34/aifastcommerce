from pydantic import BaseModel
from typing import Optional


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str]


class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True
