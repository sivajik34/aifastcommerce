"""
Pydantic schemas for the assistant API
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for chat interactions."""
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., min_length=1, description="User's message to the assistant")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "4e4e90b8-3bde-4e7c-89c4-cb6210c4d9f7",
                "message": "Show me product id 1"
            }
        }


class ProductInfo(BaseModel):
    """Schema for product information in chat responses."""
    product_id: int
    name: str
    price: float
    stock: int
    status: str = Field(description="Product availability status")


class ChatResponse(BaseModel):
    """Response schema for chat interactions."""
    response: str = Field(..., description="Assistant's response to the user")
    products: List[ProductInfo] = Field(
        default_factory=list, 
        description="List of products mentioned in the conversation"
    )
    message_count: int = Field(
        default=0, 
        description="Total number of messages in the conversation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "I found the product you're looking for! It's currently in stock.",
                "products": [
                    {
                        "product_id": 456,
                        "name": "Wireless Headphones",
                        "price":2500,
                        "stock":20,
                        "status":"in stock"
                    }]
            }
        }