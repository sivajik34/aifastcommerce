from typing import List, Literal
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.graph import MessagesState
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage, AIMessage

from db.session import get_db
from contextlib import asynccontextmanager

from modules.catalog.service import get_product_by_id
from modules.cart.service import add_to_cart as svc_add_to_cart
from modules.checkout.service import create_order
from modules.cart.schema import CartItemCreate
from modules.checkout.schema import OrderCreate, OrderItemCreate

# --- DB session helper ---
@asynccontextmanager
async def get_db_session():
    async with get_db() as session:
        yield session

# --- Tool Schemas ---

class ViewProductInput(BaseModel):
    product_id: int

class AddToCartInput(BaseModel):
    user_id: int
    product_id: int
    quantity: int

class PlaceOrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float

class PlaceOrderInput(BaseModel):
    user_id: int
    items: List[PlaceOrderItem]

# --- Tool Functions ---
@tool(return_direct=True)
async def done():
    """Signal that the agent is done with all tool calls."""
    return "Done"
@tool
class Question(BaseModel):
      """Question to ask user."""
      content: str

@tool(args_schema=ViewProductInput, return_direct=True)
async def view_product(product_id: int):
    """View product details including name, price, and stock by product_id."""
    async with get_db_session() as db:
        product = await get_product_by_id(product_id, db)
        print("calling product")
        if product:
            return {
                "name": product.name,
                "price": float(product.price),
                "stock": product.stock
            }
        return "Product not found."

@tool(args_schema=AddToCartInput, return_direct=True)
async def add_to_cart(user_id: int, product_id: int, quantity: int):
    """Add a product to a user's cart using user_id, product_id, and quantity."""
    async with get_db_session() as db:
        item = CartItemCreate(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        result = await svc_add_to_cart(item, db)
        return f"Added to cart: Product {result.product_id} x {result.quantity}"

@tool(args_schema=PlaceOrderInput, return_direct=True)
async def place_order(user_id: int, items: List[PlaceOrderItem]):
    """Place an order for a user with a list of items including product_id, quantity, and price."""
    total = sum(item.quantity * item.price for item in items)
    order_items = [OrderItemCreate(**item.dict()) for item in items]
    order_data = OrderCreate(user_id=user_id, total_amount=total, items=order_items)

    async with get_db_session() as db:
        order = await create_order(order_data, db)
        return f"Order placed! Order ID: {order.id}, Total: {order.total_amount}"

# ---- Tools List ----
tools = [view_product, add_to_cart, place_order,done,Question]
#for t in tools:
#    print(f"Tool type: {type(t)}, repr: {t!r}")

tools_by_name = {tool.name: tool for tool in tools}

# ---- Router Schema ----
class RouterSchema(BaseModel):
    reasoning: str = Field(description="Step-by-step reasoning behind the classification.")
    classification: Literal["ignore", "respond"] = Field(description="The classification of the user input.")

class AgentState(MessagesState):
    user_input: str
    user_id: str
    classification_decision: Literal["ignore", "respond"]

# ---- LLM Setup ----
llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=True)
llm_with_tools = llm.bind_tools(tools, tool_choice="any",parallel_tool_calls=False)
llm_router = llm.with_structured_output(RouterSchema)

triage_user_prompt = "this is user input {user_input}"
triage_system_prompt = "you are ecommerce assistant"

# ---- Triage Router ----
def triage_router(state: AgentState) -> Command:
    user_msg = state["user_input"]
    user_prompt = triage_user_prompt.format(user_input=user_msg)

    result = llm_router.invoke([
        {"role": "system", "content": triage_system_prompt},
        {"role": "user", "content": user_prompt},
    ])

    if result.classification == "respond":
        print("📧 Classification: respond")
        return Command(
            goto="response_agent",
            update={
                "messages": [HumanMessage(content=user_msg)],
                "classification_decision": result.classification,
            },
        )
    elif result.classification == "ignore":
        print("🚫 Classification: ignore")
        return Command(
            goto=END,
            update={"classification_decision": result.classification},
        )
    else:
        raise ValueError(f"Invalid classification: {result.classification}")    

# ---- Agent Reasoning LLM Node ----
def llm_call(state: AgentState):
    print("llm_call is calling")

    system_prompt = """
You are an ecommerce assistant. You can call these tools:

- view_product: Get product details by product_id.
- add_to_cart_tool: Add a product to a user's cart using user_id, product_id, and quantity.
- place_order: Place an order for a user with a list of items (product_id, quantity, price).
- Done: Call this tool with no arguments when you have completed the user's request and no further tool calls are needed.

Always call exactly one tool per turn if needed. When finished, call the Done tool.
"""

    response = llm_with_tools.invoke(
        [
            SystemMessage(content=system_prompt),
            *state["messages"]
        ]
    )
    return {"messages": state["messages"] + [response]}


import traceback

async def tool_handler(state: AgentState):
    print("calling tool handler")
    last_message = state["messages"][-1]
    tool_messages = []

    for idx, tool_call in enumerate(last_message.tool_calls):
        try:
            print(f"\n--- Tool Call [{idx}] ---")
            print(f"type: {type(tool_call)}")
            print(f"tool_call raw: {tool_call}")

            # Safe access to name, arguments, id (supporting both object and dict)
            tool_name = getattr(tool_call, "name", tool_call.get("name"))
            tool_args = getattr(tool_call, "arguments", None)
            if tool_args is None and isinstance(tool_call, dict):
                tool_args = tool_call.get("arguments") or tool_call.get("args")

            tool_id = getattr(tool_call, "id", tool_call.get("id"))

            print(f"Parsed tool_name: {tool_name}")
            print(f"Parsed tool_args: {tool_args}")
            print(f"Parsed tool_id: {tool_id}")

            # Lookup and call tool
            tool = tools_by_name[tool_name]
            result = await tool.ainvoke(tool_args)
            tool_messages.append(ToolMessage(tool_call_id=tool_id, content=result))

        except Exception as e:
            print(f"❌ Error during tool_call [{idx}]: {e}")
            traceback.print_exc()
            tool_messages.append(
                ToolMessage(
                    tool_call_id=tool_id or f"unknown-{idx}",
                    content=f"Tool error: {str(e)}"
                )
            )

    return {"messages": state["messages"] + tool_messages}


def should_continue(state: AgentState) -> Literal["tool_handler", "__end__"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            # Safe access for 'name'
            tool_name = getattr(tool_call, "name", None)
            if tool_name is None and isinstance(tool_call, dict):
                tool_name = tool_call.get("name")
            if tool_name == "done":
                return "__end__"
        return "tool_handler"
    return "__end__"


# ---- Response Agent Workflow ----
agent_workflow = StateGraph(AgentState)
agent_workflow.add_node("llm_call", llm_call)
agent_workflow.add_node("tool_handler", tool_handler)
agent_workflow.set_entry_point("llm_call")
agent_workflow.add_conditional_edges("llm_call", should_continue, {"tool_handler": "tool_handler", "__end__": END})
agent_workflow.add_edge("tool_handler", "llm_call")
response_agent = agent_workflow.compile()

# ---- Overall Workflow ----
overall_workflow = (
    StateGraph(AgentState)
    .add_node("triage_router", triage_router)
    .add_node("response_agent", response_agent)
    .set_entry_point("triage_router")
    .add_conditional_edges(
    "triage_router",
    lambda state: "response_agent" if state.get("classification_decision") == "respond" else END,
    {"response_agent": "response_agent", END: END}
)
    .compile()
)