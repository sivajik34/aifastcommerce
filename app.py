import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import re
import json
import logging
from collections.abc import AsyncGenerator
from langgraph.types import Command
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from utils.memory import store
from utils.embedding import initialize_embeddings_and_retriever
from llm.factory import get_llm_strategy
from utils.log import Logger
from supervisors.registry import TEAM_REGISTRY, TeamConfig
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages import convert_to_messages

from langchain_core.messages import HumanMessage, AIMessageChunk
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.types import Command
import chainlit as cl
from dotenv import load_dotenv

# -------------------------------
# ✅ Setup Logging and Environment
# -------------------------------
logger = Logger(name="magento_supervisor", log_file="Logs/app.log", level=logging.DEBUG)
load_dotenv()

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



@cl.on_chat_resume
async def on_chat_resume(thread):
    pass

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("admin", "admin"):
        logger.info("authentication success")
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
        
    else:
        logger.info("authenticatio failed")
        return None

# -------------------------------
# ✅ Utilities
# -------------------------------
def load_prompt_text(filepath="top_level_prompt.txt") -> str:
    base_path = os.path.dirname(__file__)
    full_path = os.path.join(base_path, filepath)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

def initialize_llm() -> object:
    service_name = os.getenv("LLM_SERVICE", "openai").lower()
    strategy = get_llm_strategy(service_name, "")
    return strategy.initialize()

def build_teams(llm) -> dict:
    return {team.name: team.load_team(llm) for team in TEAM_REGISTRY}

def build_supervisor(llm, teams: dict, checkpointer):
    from langgraph_supervisor.handoff import create_forward_message_tool

    forwarding_tool = create_forward_message_tool("top_level_supervisor")
    return create_supervisor(
        list(teams.values()),
        model=llm,
        supervisor_name="top_level_supervisor",
        prompt=load_prompt_text(),
        output_mode="full_history",
        tools=[forwarding_tool] 
    ).compile(checkpointer=checkpointer, store=store, name="top_level_supervisor")

def build_user_messages(user_input: str, retriever) -> list[dict]:
    user_input = user_input.content
    relevant_docs = retriever.invoke(user_input)
    context_text = "\n\n".join(doc.page_content for doc in relevant_docs)
    messages = []

    if context_text.strip():
        messages.append({
            "role": "system",
            "content": f"Documentation Context:\n{context_text}"
        })

    messages.append({
        "role": "user",
        "content": user_input
    })

    return messages


def pretty_print_message(message, indent=False):
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)

def pretty_print_messages(update, last_message=False):
    is_subgraph = False

    # ✅ CASE 1: Direct AIMessage or ToolMessage
    if isinstance(update, (AIMessage, ToolMessage)):
        print(f"Direct message of type {type(update).__name__}:\n")
        pretty_print_message(update)
        print("\n")
        return

    # ✅ CASE 2: Tuple (namespace, update_dict)
    if isinstance(update, tuple) and len(update) == 2:
        ns, actual_update = update

        if isinstance(ns, (list, tuple)) and len(ns) > 0 and isinstance(ns[-1], str):
            graph_id = ns[-1].split(":")[0]
            print(f"Update from subgraph {graph_id}:\n")
            is_subgraph = True
            update = actual_update
        elif isinstance(ns, (AIMessage, ToolMessage)):
            print(f"Direct message of type {type(ns).__name__}:\n")
            pretty_print_message(ns)
            print("\n")
            return    
        else:
            logger.warning(f"⚠️ Unexpected type for namespace (ns) {type(ns)}, skipping subgraph print.")
            return

    # ✅ CASE 3: Supervisor update dict
    if not isinstance(update, dict):
        logger.warning(f"⚠️ Unexpected update type: {type(update)}. Skipping.")
        return

    for node_name, node_update in update.items():
        update_label = f"Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label

        print(update_label + "\n")

        try:
            if isinstance(node_update, dict) and "messages" in node_update:
                raw_messages = node_update["messages"]
                messages = convert_to_messages(raw_messages)

                if last_message:
                    messages = messages[-1:]

                for m in messages:
                    pretty_print_message(m, indent=is_subgraph)
                print("\n")
            else:
                logger.warning(f"⚠️ Skipping node {node_name} due to unexpected structure: {type(node_update)}")

        except Exception as e:
            logger.error(f"❌ Error in message conversion: {e}")


@cl.on_message
async def main(message: cl.Message,came_from_resume=None,command=""):
    answer = cl.Message(content="")
    #await answer.send()

    config: RunnableConfig = {
        "configurable": {"thread_id": cl.context.session.thread_id}
    }    

    embeddings, retriever = initialize_embeddings_and_retriever()
    llm = initialize_llm()
    teams = build_teams(llm)
    db_url = os.getenv("DATABASE_URL")

    async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
        #await checkpointer.setup()
        supervisor = build_supervisor(llm, teams, checkpointer)
        #print(supervisor.get_graph().draw_mermaid())
        config = {
            "configurable": {"thread_id": cl.context.session.thread_id},
            "recursion_limit": 50
        }

        if came_from_resume:
            action={}
            command = Command(resume=[action])
            async for mode, step in supervisor.astream(
                command,
                config=config,
                stream_mode=["messages", "updates"]
            ):
                try:
                    message = step[0] if isinstance(step, tuple) else step

                    if isinstance(message, dict) and "__interrupt__" in message:
                        await cl.Message(content=extract_interrupt_message(message)).send()
                        return   # Stop further streaming on interruption

                    if is_valid_ai_message(message):
                        logger.info(f"✅ Yielding AI content: {message.content}")
                        for token in message.content:
                            await answer.stream_token(token)                        
                except Exception as e:
                    logger.error(f"❌ Streaming error: {e}")
        else:
            messages = build_user_messages(message, retriever)
            async for mode, step in supervisor.astream(
                {"messages": messages},
                config=config,
                stream_mode=["messages", "updates"]
            ):  
                try:
                    message = step[0] if isinstance(step, tuple) else step

                    if isinstance(message, dict) and "__interrupt__" in message:
                        await cl.Message(content=extract_interrupt_message(message)).send()
                        return   # Stop further streaming on interruption

                    if is_valid_ai_message(message):
                        logger.info(f"✅ Yielding AI content: {message.content}")
                        for token in message.content:
                            await answer.stream_token(token)                        
                except Exception as e:
                    logger.error(f"❌ Streaming error: {e}")
        await answer.send()