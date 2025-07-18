import json
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from modules.assistant.schema import ChatRequest
from modules.assistant.agent import overall_workflow
from shared.redisclient import redis_client  

router = APIRouter(prefix="/assistant", tags=["assistant"])

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    try:
        user_id = request.user_id  # 👈 must be passed from frontend/client
        redis_key = f"chat:{user_id}:history"

        # Load chat history from Redis
        history_json = redis_client.get(redis_key)
        messages = json.loads(history_json) if history_json else []
        result = await overall_workflow.ainvoke({"user_input": request.message})
        
        # Build message objects from JSON
        def deserialize(msg):
            from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
            if msg["role"] == "user":
                return HumanMessage(content=msg["content"])
            elif msg["role"] == "assistant":
                return AIMessage(content=msg["content"])
            elif msg["role"] == "tool":
                return ToolMessage(tool_call_id=msg.get("tool_call_id", "t1"), content=msg["content"])
            elif msg["role"] == "system":
                return SystemMessage(content=msg["content"])
            else:
                return HumanMessage(content=msg["content"])  # fallback

        message_objects = [deserialize(m) for m in messages]

        # Run workflow
        state = {
            "user_input": request.message,
            "user_id": user_id,
            "classification_decision": None,
            "messages": message_objects
        }
        result = await overall_workflow.ainvoke(state)

        # Extract updated messages
        updated_messages = result.get("messages", [])

        # Save updated history to Redis (as JSON)
        history = [{"role": m.type, "content": m.content} for m in updated_messages]
        redis_client.set(redis_key, json.dumps(history), ex=3600)

        return {
            "response": updated_messages[-1].content if updated_messages else "",
            "messages": history,
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

