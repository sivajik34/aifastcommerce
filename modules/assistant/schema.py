# modules/assistant/schema.py
from pydantic import BaseModel, Field
from typing import Optional,List,Dict,Any

class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool messages")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls for AI messages")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message")
    user_id: str = Field(..., description="User ID for maintaining chat history")
    history: Optional[List[ChatHistoryMessage]] = Field(default=[], description="Previous chat history")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The assistant's response")
    history: List[ChatHistoryMessage] = Field(..., description="Updated chat history")
    products: Optional[List[Dict[str, Any]]] = Field(default=[], description="Product recommendations")