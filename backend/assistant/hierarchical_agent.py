import os
import logging
from dotenv import load_dotenv
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

# -------------------------------
# ✅ Setup Logging and Environment
# -------------------------------
logger = Logger(name="magento_supervisor", log_file="Logs/app.log", level=logging.DEBUG)
load_dotenv()

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
            messages = convert_to_messages(node_update["messages"])
            if last_message:
                messages = messages[-1:]

            for m in messages:
                pretty_print_message(m, indent=is_subgraph)
            print("\n")

        except Exception as e:
            logger.error(f"❌ Error in message conversion: {e}")

# -------------------------------
# ✅ Main Execution
# -------------------------------
async def run_workflow_stream(
    user_input: str,
    command: Command,
    session_id: str,
    came_from_resume: bool = False
) -> AsyncGenerator[str, None]:

    embeddings, retriever = initialize_embeddings_and_retriever()
    llm = initialize_llm()
    teams = build_teams(llm)
    db_url = os.getenv("DATABASE_URL")

    async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
        supervisor = build_supervisor(llm, teams, checkpointer)
        print(supervisor.get_graph().draw_mermaid())
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 50
        }

        if came_from_resume:
            async for mode, step in supervisor.astream(
                command,
                config=config,
                stream_mode=["messages", "updates"]
            ):
                yield step
        else:
            messages = build_user_messages(user_input, retriever)
            async for mode, step in supervisor.astream(
                {"messages": messages},
                config=config,
                stream_mode=["messages", "updates"]
            ):
                pretty_print_messages(step)                
                yield step
