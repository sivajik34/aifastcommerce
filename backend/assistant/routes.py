"""
FastAPI routes for the assistant module
"""
import traceback
import logging
import re
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import interrupt
from langgraph.types import Command
from fastapi import Body
from fastapi.responses import StreamingResponse
from collections.abc import AsyncGenerator
from .schema import ChatRequest, ChatResponse
from .hierarchical_agent import run_workflow_stream
from utils.log import Logger
from .chat_history import chat_history_manager
from fastapi import BackgroundTasks

logger = Logger(name="agent_routes", log_file="Logs/app.log", level=logging.DEBUG)

router = APIRouter(prefix="/assistant", tags=["assistant"])
 
def to_serializable(obj):
    if hasattr(obj, "dict"):
        return obj.dict()  # for Pydantic
    elif hasattr(obj, "__dict__"):
        return obj.__dict__  # for regular classes
    elif isinstance(obj, (list, tuple)):
        return [to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    return str(obj)  # fallback for simple types

def extract_interrupt_message(message: dict) -> str:
    """Format and return the interruption message."""
    interrupt = message["__interrupt__"][0]
    logger.info(f"🛑 Workflow interrupted. Awaiting user input: {interrupt.value}")

    if isinstance(interrupt.value, list) and len(interrupt.value) > 0:
        value = interrupt.value[0]
    else:
        value = {}

    action_request = value.get("action_request", {})
    tool_name = action_request.get("action", "unknown")
    args = action_request.get("args", {})

    logger.info(f"Interrupt tool: {tool_name}, args: {args}")

    return json.dumps({
        "response": str(interrupt.value),
        "interruption": {
            "type": tool_name,
            "message": value.get("description", ""),
            "args": to_serializable(args)
        }
    })

def is_meaningful_response(content: str) -> bool:
    lower = content.lower()
    return (
        "transferring" not in lower and
        "transferred" not in lower and
        not lower.startswith("transferring back to") and
        not lower.startswith("successfully transferred") and
        not content.startswith("i have successfully") and
        not content.startswith("if you have any further")
    )

def is_valid_ai_message(message: AIMessage) -> bool:
    name = getattr(message, "name", "")
    if name is None:
        name = ""
    return (
        isinstance(message, AIMessage)
        and message.content.strip()
        and is_meaningful_response(message.content)
        and re.match(r".*_agent$", name)
    )

async def stream_agent_response(
    user_input: str,
    command: Command,
    session_id: str,
    came_from_resume: bool = False
) -> AsyncGenerator[str, None]:
    try:
        result_stream = run_workflow_stream(user_input, command, session_id, came_from_resume)
        async for chunk in result_stream:
            message = chunk[0] if isinstance(chunk, tuple) else chunk

            if isinstance(message, dict) and "__interrupt__" in message:
                yield extract_interrupt_message(message)
                return  # Stop further streaming on interruption

            if is_valid_ai_message(message):
                logger.info(f"✅ Yielding AI content: {message.content}")
                yield message.content
            #else:
            #    pass
                #if isinstance(message, str) and is_meaningful_response(message.content):
                #    yield message.content.strip()
                #else:
                #    pass
                    #if isinstance(message, AIMessage) and message.content:
                    #    yield message.content.strip()
                    #else:
                    #    yield "sorry, there is no proper response."    


    except Exception as e:
        logger.error(f"❌ Error in stream_agent_response: {e}\n{traceback.format_exc()}")
        yield "\n[Error] Something went wrong during streaming."

@router.post("/chat/stream")
async def chat_with_agent_stream(request: ChatRequest, background_tasks: BackgroundTasks):
    try:
        session_id = request.session_id
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        
        user_msg = HumanMessage(content=request.message)
        await chat_history_manager.add_message(session_id, user_msg)

        logger.info(f"💬 (Streaming) Processing chat for user {session_id}: {request.message[:50]}...")

        bot_response_text = ""

        async def wrapped_stream_agent_response():
            nonlocal bot_response_text
            async for chunk in stream_agent_response(
                user_input=request.message,
                command="",
                session_id=session_id,
                came_from_resume=False
            ):
                
                bot_response_text += chunk
                yield chunk

        async def save_bot_message_after_stream():
            # Wait until streaming_generator is fully consumed
            # This function will be called by BackgroundTasks after response is sent
            if bot_response_text.strip():
                bot_message = AIMessage(content=bot_response_text)
                await chat_history_manager.add_message(session_id, bot_message)

        # Add background task to save bot message after streaming response completes
        background_tasks.add_task(save_bot_message_after_stream)        

        # Return streaming response but also save the entire bot response when done
        response_stream = wrapped_stream_agent_response()

        return StreamingResponse(response_stream, media_type="text/plain")

    except Exception as e:
        logger.error(f"❌ Streaming chat error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "response": "Internal server error occurred during streaming."}
        )


@router.post("/resume")
async def resume_agent_stream(
    background_tasks: BackgroundTasks,
    session_id: str = Body(..., embed=True),
    action: dict = Body(..., embed=True)
):
    try:
        logger.info(f"♻️ Resuming agent for session_id: {session_id} with action: {action}")
        command = Command(resume=[action])
       
        await chat_history_manager.add_message(
            session_id,
            HumanMessage(content=f"[Resumed Action] {action}")
        )

        bot_response_text = ""

        async def streaming_generator():
            nonlocal bot_response_text
            async for chunk in stream_agent_response(
                user_input="",
                command=command,
                session_id=session_id,
                came_from_resume=True
            ):
                bot_response_text += chunk
                yield chunk

        async def save_bot_message_after_stream():
            if bot_response_text.strip():
                
                bot_message = AIMessage(content=bot_response_text)
                await chat_history_manager.add_message(session_id, bot_message)

        background_tasks.add_task(save_bot_message_after_stream)

        return StreamingResponse(streaming_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"❌ Error while streaming: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "response": "Unable to resume the agent due to an internal error."}
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
        from .chat_history import chat_history_manager
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

# deprecated
def extract_final_response(result) -> str:
    """
    Extracts the most recent meaningful AIMessage from the LangGraph result.
    Prefers *_agent messages with informative, user-facing content.
    """
    messages = result.get("messages", [])

    def is_meaningful(msg: AIMessage) -> bool:
        if not isinstance(msg, AIMessage) or not msg.content:
            return False
        content = msg.content.strip().lower()
        return (
            not msg.tool_calls
            and "transferred" not in content
            and not content.startswith("transferring")
            and not content.startswith("if you have any further")
            and not content.startswith("i have successfully")
        )

    for msg in reversed(messages):
        if (
            isinstance(msg, AIMessage)
            and re.match(r".*_agent$", getattr(msg, "name", ""))
            and is_meaningful(msg)
        ):
            return msg.content.strip()

    for msg in reversed(messages):
        if is_meaningful(msg):
            return msg.content.strip()

    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content.strip()

    return "No meaningful response found."