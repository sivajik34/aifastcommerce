"""
FastAPI routes for the assistant module
"""
import traceback
import logging
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage
from langgraph.types import interrupt
from langgraph.types import Command
from fastapi import Body

from .schema import ChatRequest, ChatResponse
from .hierarchical_agent import run_workflow
from .hierarchical_agent import run_workflow_stream
from utils.log import Logger

logger = Logger(name="agent_routes", log_file="Logs/app.log", level=logging.DEBUG)

router = APIRouter(prefix="/assistant", tags=["assistant"])


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
        logger.info("🚀 Starting agent workflow...")

        result = run_workflow(request.message, "",str(session_id))
        logger.info(result)

        if "__interrupt__" in result and isinstance(result["__interrupt__"], list):
            interrupt = result["__interrupt__"][0]
            logger.info(f"🛑 Workflow interrupted. Awaiting user input: {interrupt.value}")

            # 💡 Extract from interrupt.value[0]
            value = interrupt.value[0]
            action_request = value.get("action_request", {})
            tool_name = action_request.get("action", "unknown")
            args = action_request.get("args", {})

            logger.info(f"Interrupt tool: {tool_name}, args: {args}")

            return JSONResponse(
                content={
                    "response": str(interrupt.value),
                    "interruption": {
                        "type": tool_name,  # ✅ Now correctly "delete_product"
                        "message": value.get("description", ""),
                        "args": args
                    }
                }
            )



        result_messages = result.get("messages", [])
        for m in result_messages:
            m.pretty_print()

        response_text = extract_final_response(result)
        logger.info(f"✅ Response ready: {response_text[:50]}...")

        return ChatResponse(response=response_text)

    except HTTPException:
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


@router.post("/resumebak", response_model=ChatResponse)
def resume_agent(
    session_id: str = Body(..., embed=True),
    action: dict = Body(..., embed=True)
):
    """
    Resume the paused agent workflow after an interruption (e.g., tool call approval/edit).
    """
    try:
        logger.info(f"♻️ Resuming agent for session_id: {session_id} with action: {action}")

        # Build the Command object with the resume action
        command = Command(resume=[action])
        
        result = run_workflow("",command, session_id,True)

        logger.info("✅ Agent resumed successfully.")
        result_messages = result.get("messages", [])
        for m in result_messages:
            m.pretty_print()

        response_text = extract_final_response(result)

        return ChatResponse(response=response_text)

    except Exception as e:
        logger.error(f"❌ Failed to resume agent: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "response": "Unable to resume the agent due to an internal error."
            }
        )

from fastapi.responses import StreamingResponse
from collections.abc import AsyncGenerator
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
@router.post("/chat/stream")
async def chat_with_agent_stream(request: ChatRequest):
    """
    Streaming version of the assistant chat endpoint.
    Streams response chunks as they are generated by LangGraph.
    """
    try:
        session_id = request.session_id
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        logger.info(f"💬 (Streaming) Processing chat for user {session_id}: {request.message[:50]}...")

        async def stream_response() -> AsyncGenerator[str, None]:
            try:
                result_stream = run_workflow_stream(request.message, "", str(session_id))  # This must return an async generator
                # Handle interrupt if result_stream is not a generator (e.g., dict with __interrupt__)
                
            
                async for chunk in result_stream:
                    
                    message = chunk[0] if isinstance(chunk, tuple) else chunk
                    if isinstance(message, dict) and "__interrupt__" in message:
                        interrupt = message["__interrupt__"][0]
                        logger.info(f"🛑 Workflow interrupted. Awaiting user input: {interrupt.value}")

                        value = interrupt.value[0]
                        action_request = value.get("action_request", {})
                        tool_name = action_request.get("action", "unknown")
                        args = action_request.get("args", {})

                        logger.info(f"Interrupt tool: {tool_name}, args: {args}")
                        import json
                        yield json.dumps({
        "response": str(interrupt.value),
        "interruption": {
            "type": tool_name,
            "message": value.get("description", ""),
            "args": args
        }
    })
                        return
                       
                    # Only yield non-empty AI messages that aren't tool calls
                    if isinstance(message, AIMessage):
                        
                        if message.content.strip():
                            
                            if is_meaningful_response(message.content) and re.match(r".*_agent$", getattr(message, "name", "")):
                                logger.info(f"✅ Yielding AI content: {message.content}")
                                yield message.content
                        else:
                            
                            pass
                            #logger.debug(f"🛑 Skipping AIMessage with tool_calls or empty content: {message}")
                    else:
                        
                        pass
                        #logger.debug(f"⚠️ Skipping non-AIMessage type: {message}")

                    #if isinstance(message, str):
                    #    yield message
                   
            except Exception as e:
                logger.error(f"❌ Error while streaming: {e}\n{traceback.format_exc()}")
                yield "\n[Error] Something went wrong during streaming."

        return StreamingResponse(stream_response(), media_type="text/plain")

    except Exception as e:
        logger.error(f"❌ Streaming chat error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "response": "Internal server error occurred during streaming."
            }
        )

@router.post("/resume")
def resume_agent_stream(
    session_id: str = Body(..., embed=True),
    action: dict = Body(..., embed=True)
):
    """
    Resume the paused agent workflow after an interruption (e.g., tool call approval/edit).
    """
    try:
        logger.info(f"♻️ Resuming agent for session_id: {session_id} with action: {action}")

        # Build the Command object with the resume action
        command = Command(resume=[action])       
        
        async def stream_response() -> AsyncGenerator[str, None]:
            result_stream = run_workflow_stream("",command, session_id,True)  # This must return an async generator
            async for chunk in result_stream:
                try:        
                        
                    message = chunk[0] if isinstance(chunk, tuple) else chunk
                    #may be need to add interruption here
                    
                    # Only yield non-empty AI messages that aren't tool calls
                    if isinstance(message, AIMessage):
                        
                        if message.content.strip():
                            
                            if is_meaningful_response(message.content) and re.match(r".*_agent$", getattr(message, "name", "")):
                                logger.info(f"✅ Yielding AI content-resume: {message.content}")
                                yield message.content
                        else:
                           
                            pass
                            #logger.debug(f"🛑 Skipping AIMessage with tool_calls or empty content: {message}")
                    else:
                        
                        pass
                        #logger.debug(f"⚠️ Skipping non-AIMessage type: {message}")

                    #if isinstance(message, str):
                    #    yield message
                except Exception as e:
                    logger.error(f"❌ Error while streaming-resume: {e}\n{traceback.format_exc()}")
                    yield "\n[Error] Something went wrong during streaming-resume."                       
            

        return StreamingResponse(stream_response(), media_type="text/plain")        

    except Exception as e:
        logger.error(f"❌ Error while streaming: {e}\n{traceback.format_exc()}")
        #yield "\n[Error] Something went wrong during streaming."
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "response": "Unable to resume the agent due to an internal error."
            }
        )    


@router.delete("/chat/{session_id}")
async def clear_chat_history(session_id: str):
    """
    Clear chat history for a specific user.
    
    Useful for testing or when users want to start fresh conversations.
    """
    try:
        from .chat_history import chat_history_manager
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