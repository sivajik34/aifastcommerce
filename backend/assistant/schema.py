"""
Pydantic schemas for the assistant API
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for chat interactions."""
    session_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., min_length=1, description="User's message to the assistant")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "4e4e90b8-3bde-4e7c-89c4-cb6210c4d9f7",
                "message": "Show me product id 1"
            }
        }

class ChatResponse(BaseModel):
    """Response schema for chat interactions."""
    response: str = Field(..., description="Assistant's response to the user")