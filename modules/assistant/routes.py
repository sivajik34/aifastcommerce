"""
FastAPI routes for the assistant module
"""
import os
import psycopg
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage
from langchain_postgres import PostgresChatMessageHistory

from .schema import ChatRequest, ChatResponse
from .supervisor_agent import run_workflow
from .chat_history import chat_history_manager
from utils.log import Logger

logger=Logger(name="agent_routes", log_file="Logs/app.log", level=logging.DEBUG)

router = APIRouter(prefix="/assistant", tags=["assistant"])

def get_message_history(session_id: str):
    """Create a Postgres-backed message history object"""
    return PostgresChatMessageHistory(
        "chat_message_history",
        session_id,
        sync_connection=psycopg.connect(os.getenv("CON_STR"))
    )

def is_useful_message(msg):
    if isinstance(msg, AIMessage):
        if msg.name == "supervisor":
            return False
        if msg.content and msg.content.strip().lower().startswith("transferring"):
            return False
        if "request should be handled" in msg.content.lower():
            return False
    return True

def extract_response_text(messages) -> str:
    """
    Extract the most relevant AI message that is:
    - Not from the 'supervisor' agent
    - Not a system-like handoff message (e.g., "Transferring to...")
    - Has actual content
    """
    # Step 1: Filter AI messages with meaningful content
    candidate_msgs = [
        msg for msg in messages
        if isinstance(msg, AIMessage)
        and msg.name != "supervisor"
        and msg.content
        and not msg.content.strip().lower().startswith("transferring")
        and not msg.content.strip().lower().startswith("request was handled by")
    ]

    if candidate_msgs:
        return candidate_msgs[-1].content.strip()

    # Step 2: Fallback to last non-empty AI message
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content.strip()

    # Step 3: Nothing found
    return "I'm here to help! Please ask your question again."

def extract_products_from_messages(messages) -> list:
    """Extract product information mentioned in the conversation."""
    products = []
    # This could be enhanced to parse tool results and extract product data
    # For now, returning empty list - can be implemented based on specific needs
    return products


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
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

        # Load existing chat history from PostgreSQL
        #previous_messages = await chat_history_manager.get_recent_messages(
        #    str(session_id), 
        #    limit=20  # Keep last 20 messages for context
        #)
        history  = get_message_history(session_id)

        previous_messages = history.messages
        
        logger.info(f"📚 Loaded {len(previous_messages)} previous messages")        

        # Run the agent workflow
        logger.info("🚀 Starting agent workflow...")

        result=await run_workflow(request.message, str(session_id), previous_messages+ [HumanMessage(content=request.message)])
        logger.debug(f"🧪 Raw result from workflow: {result}")        
        
        # Extract the new messages that were added during this interaction
        result_messages = result.get("messages", [])
        updated_messages = [msg for msg in result_messages if is_useful_message(msg)]
        #memory.save_context({"input": user_input}, {"output": extract_response_text(useful_messages)})
        new_messages = updated_messages[len(previous_messages):]
        
        logger.info(f"📤 Generated {len(new_messages)} new messages")

        # Save new messages to PostgreSQL
        #if new_messages:
        #    await chat_history_manager.add_messages(str(session_id), new_messages)
        #    logger.info("💾 Saved new messages to database")

        if new_messages:
            # Save user message first
            history.add_user_message(request.message)

            # Then save each AI message
            for msg in new_messages:
                if isinstance(msg, AIMessage):
                    history.add_ai_message(msg.content)
            logger.info("💾 Saved new messages to Postgres")

        # Extract response for the user
        response_text = extract_response_text(updated_messages)
        
        # Extract any product information (for frontend integration)
        products = extract_products_from_messages(updated_messages)

        logger.info(f"✅ Response ready: {response_text[:50]}...")

        return ChatResponse(
            response=response_text,
            products=products,
            message_count=len(updated_messages)
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