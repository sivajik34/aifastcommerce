"""
FastAPI routes for the assistant module
"""
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage

from .schema import ChatRequest, ChatResponse
from .agent import overall_workflow
from .chat_history import chat_history_manager


router = APIRouter(prefix="/assistant", tags=["assistant"])


def extract_response_text(messages) -> str:
    """Extract the most recent AI response from the message history."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content.strip():
            return msg.content.strip()
    return "I'm here to help! Please let me know what you'd like to do."


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
        user_id = request.user_id
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        print(f"💬 Processing chat for user {user_id}: {request.message[:50]}...")

        # Load existing chat history from PostgreSQL
        previous_messages = await chat_history_manager.get_recent_messages(
            str(user_id), 
            limit=20  # Keep last 20 messages for context
        )
        
        print(f"📚 Loaded {len(previous_messages)} previous messages")

        # Create initial state with existing conversation history
        state = {
            "user_input": request.message,
            "user_id": str(user_id),
            "classification_decision": None,
            "messages": previous_messages
        }

        # Run the agent workflow
        print("🚀 Starting agent workflow...")
        result = await overall_workflow.ainvoke(state)
        
        # Extract the new messages that were added during this interaction
        updated_messages = result.get("messages", [])
        new_messages = updated_messages[len(previous_messages):]
        
        print(f"📤 Generated {len(new_messages)} new messages")

        # Save new messages to PostgreSQL
        if new_messages:
            await chat_history_manager.add_messages(str(user_id), new_messages)
            print("💾 Saved new messages to database")

        # Extract response for the user
        response_text = extract_response_text(updated_messages)
        
        # Extract any product information (for frontend integration)
        products = extract_products_from_messages(updated_messages)

        print(f"✅ Response ready: {response_text[:50]}...")

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
        print(f"❌ Chat error: {error_msg}")
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "error": error_msg,
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again.",
                "products": [],
                "message_count": 0
            }
        )


@router.delete("/chat/{user_id}")
async def clear_chat_history(user_id: str):
    """
    Clear chat history for a specific user.
    
    Useful for testing or when users want to start fresh conversations.
    """
    try:
        await chat_history_manager.clear_session(user_id)
        print(f"🗑️ Cleared chat history for user {user_id}")
        
        return {"message": f"Chat history cleared for user {user_id}"}
    
    except Exception as e:
        print(f"❌ Error clearing chat history: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to clear chat history: {str(e)}"
        )


@router.get("/chat/{user_id}/history")
async def get_chat_history(user_id: str, limit: int = 50):
    """
    Retrieve chat history for a specific user.
    
    Useful for debugging or providing conversation context to other services.
    """
    try:
        messages = await chat_history_manager.get_recent_messages(user_id, limit)
        
        # Convert messages to a serializable format
        history = []
        for msg in messages:
            history.append({
                "type": msg.type,
                "content": msg.content,
                "timestamp": getattr(msg, 'timestamp', None)
            })
        
        return {
            "user_id": user_id,
            "message_count": len(history),
            "messages": history
        }
    
    except Exception as e:
        print(f"❌ Error retrieving chat history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chat history: {str(e)}"
        )