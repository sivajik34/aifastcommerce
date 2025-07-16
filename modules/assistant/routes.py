from fastapi import APIRouter
from modules.assistant.schema import ChatRequest
from modules.assistant.agent import overall_workflow  # import the compiled workflow
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/assistant", tags=["assistant"])

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    try:
        result = await overall_workflow.ainvoke({"user_input": request.message})
        
        messages = [
            {"role": msg.type, "content": msg.content}
            for msg in result.get("messages", [])
        ]

        return {"response": messages[-1]["content"] if messages else "", "messages": messages}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

