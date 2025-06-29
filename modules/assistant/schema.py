# modules/assistant/schema.py
from pydantic import BaseModel
from typing import List, Literal, Optional

class ChatMessage(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []