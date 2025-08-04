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

# Agent loaders
from agents.customer.agent import get_customer_agent
from agents.order.agent import get_order_agent
from agents.product.agent import get_product_agent
from agents.stock.agent import get_stock_agent
from agents.category.agent import get_category_agent
from agents.invoice.agent import get_invoice_agent
from agents.shipment.agent import get_shipment_agent
from agents.directory.agent import get_directory_agent

# Team builders
from supervisors.catalog_team import get_catalog_team
from supervisors.customer_team import get_customer_team
from supervisors.sales_team import get_sales_team
from supervisors.directory_supervisor import get_directory_team

logger = Logger(name="supervisor", log_file="Logs/app.log", level=logging.DEBUG)

load_dotenv()

# -------------------------------
# ✅ Centralized Supervisor Registry
# -------------------------------
SUPERVISOR_REGISTRY = [
    {
        "name": "sales_team",
        "agent_loaders": [get_order_agent, get_shipment_agent, get_invoice_agent],
        "team_loader": get_sales_team
    },
    {
        "name": "catalog_team",
        "agent_loaders": [get_product_agent, get_category_agent, get_stock_agent],
        "team_loader": get_catalog_team
    },
    {
        "name": "customer_team",
        "agent_loaders": [get_customer_agent],
        "team_loader": get_customer_team
    },
    {
        "name": "directory_team",
        "agent_loaders": [get_directory_agent],
        "team_loader": get_directory_team
    }
]

# -------------------------------
# ✅ Load top-level prompt
# -------------------------------
def load_prompt_text() -> str:
    base_path = os.path.dirname(__file__)  # directory of this script
    filepath = os.path.join(base_path, "top_level_prompt.txt")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

prompt_text = load_prompt_text()

# -------------------------------
# ✅ Initialize LLM + Teams
# -------------------------------
def initialize_llm_and_supervisors():
    service_name = os.getenv("LLM_SERVICE", "openai").lower()
    strategy = get_llm_strategy(service_name, "")
    llm = strategy.initialize()

    teams = {}
    for supervisor in SUPERVISOR_REGISTRY:
        agents = [loader(llm) for loader in supervisor["agent_loaders"]]
        team = supervisor["team_loader"](llm, agents=agents)
        teams[supervisor["name"]] = team

    return llm, teams

# -------------------------------
# ✅ Build top-level supervisor
# -------------------------------
def build_top_level_supervisor(llm, teams: dict, checkpointer):
    top_level_supervisor = create_supervisor(
        list(teams.values()),
        model=llm,
        supervisor_name="top_level_supervisor",
        prompt=prompt_text,
        output_mode="full_history"
    ).compile(checkpointer=checkpointer, store=store, name="top_level_supervisor")

    return top_level_supervisor

# -------------------------------
# ✅ Stream execution
# -------------------------------
async def run_workflow_stream(user_input: str, command: Command, session_id: str, came_from_resume: bool = False) -> AsyncGenerator[str, None]:
    embeddings, retriever = initialize_embeddings_and_retriever()
    llm, teams = initialize_llm_and_supervisors()

    DB_URI = os.getenv("DATABASE_URL")
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        supervisor = build_top_level_supervisor(llm, teams, checkpointer)

        if came_from_resume:
            async for mode, step in supervisor.astream(
                command,
                config={"configurable": {"thread_id": session_id}},
                stream_mode=["messages", "updates"]
            ):
                yield step
        else:
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

            async for mode, step in supervisor.astream(
                {"messages": messages},
                config={"configurable": {"thread_id": session_id}, "recursion_limit": 50},
                stream_mode=["messages", "updates"]
            ):
                print(step)
                print("\n")
                yield step