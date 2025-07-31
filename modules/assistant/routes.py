"""
FastAPI routes for the assistant module
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage,ToolMessage

from .schema import ChatRequest, ChatResponse
#from .supervisor_agent import run_workflow
from .hierarchical_agent import run_workflow
from .chat_history import chat_history_manager
from utils.log import Logger

logger=Logger(name="agent_routes", log_file="Logs/app.log", level=logging.DEBUG)

router = APIRouter(prefix="/assistant", tags=["assistant"])




from langchain_core.messages import AIMessage, ToolMessage, BaseMessage

import re
from langchain_core.messages import AIMessage

def extract_final_response(result) -> str:
    """
    Extracts the final meaningful AIMessage from the LangGraph result.
    Prefers messages from agents with names ending in '_agent'.
    """
    messages = result.get("messages", [])

    def is_clean_user_facing(msg: AIMessage) -> bool:
        content = msg.content.strip().lower()
        return (
            msg.content
            and not msg.tool_calls
            and "transferred" not in content
            and not content.startswith("transferring")
            and not content.startswith("i have successfully")
        )

    # Step 1: Find all AI messages from *_agent
    candidates = [
        m.content.strip()
        for m in messages
        if isinstance(m, AIMessage)
        and re.match(r".*_agent$", getattr(m, "name", ""))
        and is_clean_user_facing(m)
    ]

    if candidates:
        return max(candidates, key=len)

    # Step 2: Fallback to any meaningful AI message
    fallback_candidates = [
        m.content.strip()
        for m in messages
        if isinstance(m, AIMessage) and is_clean_user_facing(m)
    ]
    if fallback_candidates:
        return max(fallback_candidates, key=len)

    # Step 3: Fallback to last assistant message
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content.strip()

    return "No meaningful response found."




@router.post("/chat", response_model=ChatResponse)
def chat_with_agent(request: ChatRequest):
    """
    Main chat endpoint for the ecommerce assistant.
    
    Processes user messages, maintains conversation history in PostgreSQL,
    and returns AI responses with context.
    """
    try:
        session_id = request.session_id
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        logger.info(f"💬 Processing chat for user {session_id}: {request.message[:50]}...")
        # Run the agent workflow
        logger.info("🚀 Starting agent workflow...")
        result = run_workflow(request.message, str(session_id))
        logger.debug(f"🧪 Raw result from workflow: {result}")        
        
        # Extract the new messages that were added during this interaction
        result_messages = result.get("messages", [])
        #logger.info(f"result_messages:{result_messages}")
        for m in result_messages:
            m.pretty_print()
        response_text = extract_final_response(result)      
        

        logger.info(f"✅ Response ready: {response_text[:50]}...")

        return ChatResponse(
            response=response_text,            
            #message_count=len(updated_messages)
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        error_msg = f"Internal server error: {str(e)}"
        logger.error(f"❌ Chat error: {error_msg}")        
        
        return JSONResponse(
            status_code=500,
            content={
                "error": error_msg,
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again.",
                "products": [],
                "message_count": 0
            }
        )


@router.delete("/chat/{session_id}")
async def clear_chat_history(session_id: str):
    """
    Clear chat history for a specific user.
    
    Useful for testing or when users want to start fresh conversations.
    """
    try:
        await chat_history_manager.clear_session(session_id)
        logger.info(f"🗑️ Cleared chat history for user {session_id}")
        
        return {"message": f"Chat history cleared for user {session_id}"}
    
    except Exception as e:
        logger.error(f"❌ Error clearing chat history: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to clear chat history: {str(e)}"
        )


@router.get("/chat/{session_id}/history")
async def get_chat_history(session_id: str, limit: int = 50):
    """
    Retrieve chat history for a specific user.
    
    Useful for debugging or providing conversation context to other services.
    """
    try:
        messages = await chat_history_manager.get_recent_messages(session_id, limit)
        
        # Convert messages to a serializable format
        history = []
        for msg in messages:
            history.append({
                "type": msg.type,
                "content": msg.content,
                "timestamp": getattr(msg, 'timestamp', None)
            })
        
        return {
            "session_id": session_id,
            "message_count": len(history),
            "messages": history
        }
    
    except Exception as e:
        logger.error(f"❌ Error retrieving chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )