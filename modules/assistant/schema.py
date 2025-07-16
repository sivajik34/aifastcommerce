# modules/assistant/schema.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str