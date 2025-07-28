"""
Supervisor Multi-Agent Workflow for E-commerce Assistant
"""
import logging
from typing import List
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, HumanMessage,SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from modules.llm.factory import get_llm_strategy
from utils.log import Logger
from modules.magento_tools.utility_tools import tools as utiltools
from modules.magento_tools.product_tools import tools as producttools
from modules.magento_tools.customer_tools import tools as customertools
from modules.magento_tools.sales_tools import tools as salestools
import os
from dotenv import load_dotenv


logger=Logger(name="supervisor", log_file="Logs/app.log", level=logging.DEBUG)



load_dotenv()
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
# Load retriever from saved FAISS index
retriever = FAISS.load_local(
    "vectorstores/adobe_docs",
    embeddings,
    allow_dangerous_deserialization=True
).as_retriever(search_type="similarity", k=4)

# --- State Definition ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    user_input: str
    session_id: str  

# --- Agent Configuration ---
class AgentConfig:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        # ---- LLM Setup ----
        strategy = get_llm_strategy("openai", "")
        self.llm = strategy.initialize()

config = AgentConfig()

catalog_agent=create_react_agent(
            config.llm, 
            producttools+utiltools,
            name="CATALOG_AGENT",
            prompt="""You are a product specialist for an e-commerce platform.
        
            Your responsibilities:
            - Search for products based on user queries
            - Provide detailed product information including SKU, name, price, and stock status
            - Help users find products by category, price range, or specific attributes
            - Answer questions about product availability and specifications
            - After you're done with your tasks, call the done tool to signal task completion
            - also you can create , update product ,category 
            - you can assign product to given category ids
            - ask_question: Ask clarifying questions when you need more information
            - done: Signal when the task is completed
            
            Always be helpful and provide detailed product information when available.
            If you can't find what the user is looking for, suggest alternatives or ask for clarification."""
            )
        
        

customer_agent=create_react_agent(
            config.llm, 
            customertools+utiltools,
            name="CUSTOMER_AGENT",
            prompt="""You are a customer service specialist for an e-commerce platform.
        
            Your responsibilities:
            - Retrieve customer information by email
            - Create new customer accounts with proper validation
            - Handle customer account inquiries and updates
            - Assist with customer registration and profile management            
          
            - ask_question: Ask for required information when you need more information
            - Once you've fulfilled the customer’s request (e.g., retrieved their info), you MUST call the `done` tool to signal task completion.
            
            When creating customers:
            - Always ask for required fields: email, firstname, lastname
            - Password is optional but recommended
            - Address information is optional but helpful for future orders
            - Validate email format and ensure all required information is provided
            
            Be professional and ensure data privacy and security."""
        )

sales_agent=create_react_agent(
            config.llm, 
            salestools+utiltools,
            name="SALES_AGENT",
            prompt="""You are an order processing specialist for an e-commerce platform.
        
            Your responsibilities:
            - Create orders for registered customers and guest users
            - Validate customer information and product availability before processing orders
            - Handle payment method selection and order confirmation
            - Assist with order-related inquiries           
           
            - ask_question: Ask for required information when you need more information
            - done: Signal when order is completed
            
            Order Creation Process:
            1. Verify customer exists and get their information
            2. Validate all products in the order (check SKU, availability, stock)
            3. Confirm order details with customer
            4. Process the order with selected payment method
            5. Provide order confirmation
            
            Payment methods available: checkmo, banktransfer, cashondelivery
            Always verify product availability and customer details before processing orders."""
        )
 
general_agent=create_react_agent(
            config.llm, 
            utiltools,
            name="GENERAL_AGENT",
            prompt="""You are a general assistant for an e-commerce platform.
        
            Your responsibilities:
            - Handle greetings and general inquiries
            - Provide help and guidance about the platform
            - Direct users to appropriate services
            - Handle miscellaneous requests that don't fit other categories
            
            Available tools:
            - ask_question: Ask clarifying questions
            - done: Signal when interaction is complete
            
            Platform Capabilities:
            - Product search and information
            - Customer account management  
            - Order processing and management
            - General customer support
            
            Be friendly, helpful, and guide users to the appropriate services.
            If you can't handle a specific request, suggest they ask about:
            - Products (search, details, availability)
            - Customer accounts (creation, information)
            - Orders (placing orders, order status)"""
            )
rag_agent = create_react_agent(
    config.llm,
    utiltools,
    name="RAG_AGENT",
    prompt="""You are a documentation assistant who helps users by retrieving relevant knowledge from Adobe documentation.

Contextual Info:
You receive a list of relevant documents retrieved by a search engine (RAG).

Your tasks:
- Read and understand the provided document context
- Answer questions based on that context
- If unsure or if the context is insufficient, ask clarifying questions
- Once the task is complete, call the `done` tool

Always answer using the document information provided. If no good match is found, let the user know politely.
"""
)


# --- Build Workflow Graph ---
def create_supervisor_workflow():
    """Create the supervisor multi-agent workflow"""    
   
    workflow = create_supervisor(
        [catalog_agent, customer_agent,sales_agent,general_agent],
        model=config.llm,
        prompt= """You are a supervisor for an e-commerce assistant system.

        Available Agents:
        1. CATALOG_AGENT: Handles product searches, viewing product details, inventory queries, creation of product and category
        2. CUSTOMER_AGENT: Manages customer information, account creation, customer queries  
        3. SALES_AGENT: Processes orders, order creation, order management
        4. GENERAL_AGENT: Handles general queries, greetings, help requests
        

        Analyze the user's message and determine which agent should handle the request.
        If the task is complete or the user says goodbye, return FINISH.
        
        """
    )

    # Compile and run
    return workflow.compile()   
    

# --- Main Workflow Instance ---
overall_workflow = create_supervisor_workflow()

# --- Utility Functions ---
def create_initial_state(
    user_input: str, 
    session_id: str, 
    existing_messages: List[BaseMessage] = None
) -> AgentState:
    """Create initial state for the workflow"""
    if existing_messages is None:
        existing_messages = [HumanMessage(content=user_input)]
       
    
    return AgentState(
        messages=existing_messages,
        user_input=user_input,
        session_id=session_id        
    )

async def run_workflow(user_input: str, session_id: str, existing_messages: List[BaseMessage] = None):
    """Run the complete workflow with user input"""
    initial_state = create_initial_state(user_input, session_id, existing_messages)
    result = await overall_workflow.ainvoke(initial_state)
    return result

# --- Export for routes.py integration ---
__all__ = ["overall_workflow", "AgentState", "create_initial_state", "run_workflow"]