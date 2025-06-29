from fastapi import APIRouter
from modules.assistant.schema import ChatRequest
from modules.assistant.agent import ecommerce_assistant

router = APIRouter(prefix="/assistant", tags=["assistant"])

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    try:
        result = await ecommerce_assistant(request.message, request.history)
        return {
            "response": result["response"],
            "history": result["history"],  # Already a list of dicts with "role" and "content"
        }
    except Exception as e:
        return {"error": str(e)}
