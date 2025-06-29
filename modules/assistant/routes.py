from fastapi import APIRouter
from pydantic import BaseModel
from modules.assistant.agent import ecommerce_assistant

router = APIRouter(prefix="/assistant", tags=["assistant"])

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    try:
        response = await ecommerce_assistant(request.message)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}

