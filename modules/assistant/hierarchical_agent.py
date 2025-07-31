import os
import logging
from dotenv import load_dotenv
from langgraph.types import Command
from langchain_core.messages import HumanMessage, trim_messages,AIMessage
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

from langchain_community.vectorstores import FAISS
from modules.llm.factory import get_llm_strategy
from langgraph_supervisor import create_supervisor
from utils.log import Logger
from utils.memory import checkpointer,store

#from modules.magento_tools.utility_tools import tools as utiltools

from modules.agents.customer.agent import get_customer_agent
from modules.agents.order.agent import get_order_agent
from modules.agents.product.agent import get_product_agent
from modules.agents.stock.agent import get_stock_agent
from modules.agents.category.agent import get_category_agent
from modules.agents.invoice.agent import get_invoice_agent
from modules.agents.shipment.agent import get_shipment_agent

from modules.supervisors.catalog_team import get_catalog_team
from modules.supervisors.customer_team import get_customer_team
from modules.supervisors.sales_team import get_sales_team


logger=Logger(name="supervisor", log_file="Logs/app.log", level=logging.DEBUG)

load_dotenv()
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
# Load retriever from saved FAISS index
retriever = FAISS.load_local(
    "vectorstores/adobe_docs",
    embeddings,
    allow_dangerous_deserialization=True
).as_retriever(search_type="similarity", k=4)
#relevant_docs = retriever.invoke(user_input)
#context_text = "\n\n".join(doc.page_content for doc in relevant_docs)

strategy = get_llm_strategy("openai", "")
llm = strategy.initialize()

order_agent = get_order_agent(llm)
shipment_agent = get_shipment_agent(llm)
invoice_agent = get_invoice_agent(llm)
product_agent = get_product_agent(llm)
category_agent = get_category_agent(llm)
stock_agent = get_stock_agent(llm)
customer_agent = get_customer_agent(llm)

sales_team = get_sales_team(llm, agents=[order_agent, shipment_agent, invoice_agent])
catalog_team = get_catalog_team(llm, agents=[product_agent, category_agent, stock_agent])
customer_team = get_customer_team(llm, agents=[customer_agent])

# TOP LEVEL SUPERVISOR
top_level_supervisor = create_supervisor(
    [catalog_team, sales_team, customer_team],
    model=llm,
    supervisor_name="top_level_supervisor",
    prompt="""You are the Top Level Supervisor managing the entire e-commerce platform operations.

    Your teams consist of:
    1. catalog_team: Manages products, categories, and inventory
       - Product management (create, update, search, view)
       - Category organization and structure
       - Stock monitoring and inventory updates
    
    2. sales_team: Handles order fulfillment and sales operations
       - Order processing and management
       - Shipping and delivery coordination
       - Invoicing and payment processing
    
    3. customer_team: Manages customer accounts and relationships
       - Customer registration and profile management
       - Account updates and maintenance
       - Customer support and service
    
    Routing Guidelines:
    - Product/category/inventory questions → catalog_team
    - Order/shipping/billing questions → sales_team
    - Customer account/profile questions → customer_team
    
    Cross-team Coordination:
    - New customer orders require customer validation + product availability + order processing
    - Product updates may affect existing orders and customer notifications
    - Customer account changes may impact order history and preferences
    
    Always:
    - Analyze requests carefully to determine the appropriate team
    - Coordinate between teams for complex multi-step operations
    - Ensure consistent customer experience across all interactions
    - Prioritize customer satisfaction and operational efficiency
    - Handle escalations and complex issues requiring multiple team coordination
    
    Examples:
    - "Create order for customer john@email.com" → Coordinate customer_team + catalog_team + sales_team
    - "Show me product ABC-123" → catalog_team
    - "Track my order #12345" → sales_team
    - "Update my address" → customer_team
    - "Add new product and create order for it" → catalog_team + sales_team coordination
    """,
    output_mode="full_history"
).compile(checkpointer=checkpointer, store=store, name="top_level_supervisor")


def run_workflow(user_input: str, session_id: str):
    """Run the complete workflow with user input"""

    logger.info(f"user_input:{user_input}")

    result = top_level_supervisor.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        },
        config={"configurable": {"thread_id": session_id}}
    )    
    return result