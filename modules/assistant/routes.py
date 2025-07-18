import json
from fastapi import APIRouter,HTTPException
from fastapi.responses import JSONResponse
from modules.assistant.schema import ChatRequest
from modules.assistant.agent import overall_workflow
from shared.redisclient import redis_client  
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage

router = APIRouter(prefix="/assistant", tags=["assistant"])

def serialize_message(msg):
    """Convert LangChain message to JSON-serializable format"""
    base = {
        "role": msg.type,
        "content": msg.content
    }
    
    if isinstance(msg, ToolMessage):
        base["tool_call_id"] = msg.tool_call_id
        base["role"] = "tool"
    elif isinstance(msg, AIMessage):
        base["role"] = "ai"
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            base["tool_calls"] = [
                {
                    "id": tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None),
                    "name": tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None),
                    "args": tc.get("args") if isinstance(tc, dict) else getattr(tc, "arguments", {})
                }
                for tc in msg.tool_calls
            ]
    elif isinstance(msg, HumanMessage):
        base["role"] = "human"
    elif isinstance(msg, SystemMessage):
        base["role"] = "system"
    
    return base

def deserialize_message(msg_dict):
    """Convert JSON message back to LangChain message"""
    role = msg_dict.get("role")
    content = msg_dict.get("content", "")
    
    if role == "human":
        return HumanMessage(content=content)
    elif role == "ai":
        ai_msg = AIMessage(content=content)
        if "tool_calls" in msg_dict:
            ai_msg.tool_calls = msg_dict["tool_calls"]
        return ai_msg
    elif role == "tool":
        return ToolMessage(
            tool_call_id=msg_dict.get("tool_call_id", "unknown"),
            content=content
        )
    elif role == "system":
        return SystemMessage(content=content)
    else:
        return HumanMessage(content=content)  # fallback

@router.post("/chat")
async def chat_with_agent(request: ChatRequest):
    try:
        user_id = request.user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
            
        redis_key = f"chat:{user_id}:history"

        # Load chat history from Redis
        history_json = redis_client.get(redis_key)
        previous_messages = []
        
        if history_json:
            try:
                history_data = json.loads(history_json)
                previous_messages = [deserialize_message(msg) for msg in history_data]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading chat history: {e}")
                # Reset history if corrupted
                redis_client.delete(redis_key)

        # Create initial state with existing messages
        state = {
            "user_input": request.message,
            "user_id": str(user_id),
            "classification_decision": None,
            "messages": previous_messages
        }

        # Run workflow
        result = await overall_workflow.ainvoke(state)

        # Extract updated messages
        updated_messages = result.get("messages", [])
        
        # Get the last AI message content for response
        response_text = ""
        for msg in reversed(updated_messages):
            if isinstance(msg, AIMessage) and msg.content.strip():
                response_text = msg.content
                break
        
        if not response_text:
            response_text = "I'm here to help! Please let me know what you'd like to do."

        # Serialize and save updated history to Redis
        serialized_history = [serialize_message(msg) for msg in updated_messages]
        redis_client.set(redis_key, json.dumps(serialized_history), ex=3600)

        return {
            "response": response_text,
            "history": serialized_history,
            "products": []  # Add product extraction logic if needed
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )
