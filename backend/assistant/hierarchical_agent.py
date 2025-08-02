import os
import logging
import re
from dotenv import load_dotenv

from langgraph.types import Command
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from utils.memory import store
from utils.embedding import initialize_embeddings_and_retriever

from agents.customer.agent import get_customer_agent
from agents.order.agent import get_order_agent
from agents.product.agent import get_product_agent
from agents.stock.agent import get_stock_agent
from agents.category.agent import get_category_agent
from agents.invoice.agent import get_invoice_agent
from agents.shipment.agent import get_shipment_agent

from supervisors.catalog_team import get_catalog_team
from supervisors.customer_team import get_customer_team
from supervisors.sales_team import get_sales_team

from llm.factory import get_llm_strategy
from utils.log import Logger
from collections.abc import AsyncGenerator
from langchain_core.messages import AIMessage
logger = Logger(name="supervisor", log_file="Logs/app.log", level=logging.DEBUG)

load_dotenv()

def initialize_llm_and_agents():
    """Initialize LLM strategy and all agents and teams."""
    service_name = os.getenv("LLM_SERVICE", "openai").lower()
    strategy = get_llm_strategy(service_name, "")
    llm = strategy.initialize()

    # Initialize agents
    order_agent = get_order_agent(llm)
    shipment_agent = get_shipment_agent(llm)
    invoice_agent = get_invoice_agent(llm)
    product_agent = get_product_agent(llm)
    category_agent = get_category_agent(llm)
    stock_agent = get_stock_agent(llm)
    customer_agent = get_customer_agent(llm)

    # Initialize teams with agents
    sales_team = get_sales_team(llm, agents=[order_agent, shipment_agent, invoice_agent])
    catalog_team = get_catalog_team(llm, agents=[product_agent, category_agent, stock_agent])
    customer_team = get_customer_team(llm, agents=[customer_agent])

    return llm, sales_team, catalog_team, customer_team

def load_prompt_text() -> str:
    base_path = os.path.dirname(__file__)  # directory of this script
    filepath = os.path.join(base_path, "top_level_prompt.txt")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# Load prompt text once
prompt_text = load_prompt_text()


def build_top_level_supervisor(llm, sales_team, catalog_team, customer_team, checkpointer):
    """Create and compile the top level supervisor with prompt and teams."""
    
    top_level_supervisor = create_supervisor(
        [catalog_team, sales_team, customer_team],
        model=llm,
        supervisor_name="top_level_supervisor",
        prompt=prompt_text,
        output_mode="full_history"
    ).compile(checkpointer=checkpointer, store=store, name="top_level_supervisor")

    return top_level_supervisor


def run_workflow(user_input: str, command: Command, session_id: str, came_from_resume: bool = False):
    """
    Runs the complete workflow with user input.

    Args:
        user_input (str): The raw input string from the user.
        command (Command): The command structure if resuming from saved state.
        session_id (str): Unique identifier for the session/thread.
        came_from_resume (bool): Flag indicating if this invocation is from resuming a previous state.

    Returns:
        Result of the supervisor invocation.
    """
    # Initialize embeddings and retriever once on module load
    embeddings, retriever = initialize_embeddings_and_retriever()

    # Initialize LLM, agents, and teams once on module load
    llm, sales_team, catalog_team, customer_team = initialize_llm_and_agents()

    DB_URI = os.getenv("DATABASE_URL")
    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
        # Build supervisor inside the checkpoint context
        top_level_supervisor = build_top_level_supervisor(llm, sales_team, catalog_team, customer_team, checkpointer)

        if came_from_resume:
            # Resume from saved command state
            result = top_level_supervisor.invoke(
                command,
                config={"configurable": {"thread_id": session_id}}
            )
        else:
            logger.info(f"user_input: {user_input}")

            # Retrieve relevant docs from FAISS vectorstore
            relevant_docs = retriever.invoke(user_input)
            context_text = "\n\n".join(doc.page_content for doc in relevant_docs)

            messages = []

            # Include retrieved documentation context if available
            if context_text.strip():
                messages.append({
                    "role": "system",
                    "content": f"Documentation Context:\n{context_text}"
                })

            # Append actual user input
            messages.append({
                "role": "user",
                "content": user_input
            })

            # Invoke the supervisor with constructed messages
            result = top_level_supervisor.invoke(
                {"messages": messages},
                config={"configurable": {"thread_id": session_id}}
            )

        return result

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

async def run_workflow_stream(user_input: str, command: Command, session_id: str,came_from_resume: bool = False) -> AsyncGenerator[str, None]:
    embeddings, retriever = initialize_embeddings_and_retriever()
    llm, sales_team, catalog_team, customer_team = initialize_llm_and_agents()

    DB_URI = os.getenv("DATABASE_URL")
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        supervisor = build_top_level_supervisor(llm, sales_team, catalog_team, customer_team, checkpointer)
        if came_from_resume:
            # Resume from saved command state
            
            # This requires that supervisor.invoke supports streaming (like a generator)
            async for mode,step in supervisor.astream(command, config={"configurable": {"thread_id": session_id}},stream_mode=["messages","updates"]):
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

            # This requires that supervisor.invoke supports streaming (like a generator)
            async for mode, step in supervisor.astream({"messages": messages}, config={"configurable": {"thread_id": session_id}},stream_mode=["messages","updates"]):
                #print(step)
                #print("\n")
                yield step
                
